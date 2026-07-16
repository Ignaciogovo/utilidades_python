# utilidades-python:enviar_notificaciones
# Descripción: Daemon one-shot que despacha JSONs de error_system por correo y los
#              archivos en una subcarpeta `enviados/`, borrándolos tras 24h.
# __version__ = "1.0.0"
#
# Su rol: ES el script que tiene las credenciales (las lee de env vars, no las
# hardcodea). error_system.py no sabe de correos; enviar_correo.py no sabe de
# rutas ni de estado. Este script es el pegamento: lee pendientes, despacha,
# marca y limpia.
#
# Pensado para cron o systemd timer (one-shot). Sin bucle, sin sleep. Cada
# ejecución: limpia viejos → procesa pendientes → sale.
#
# Configuración (variables de entorno):
#   CARPETA_ERRORES   → carpeta donde yacen los errores_*.json pendientes.
#                       Default: "./notificaciones/" (mismo default que error_system).
#   ENVIADOS_DIR      → subcarpeta destino tras enviar. Default: <CARPETA_ERRORES>/enviados/.
#   RETENCION_HORAS   → horas mínimas en enviados/ antes de borrar. Default: "24".
#   EMAIL_GENERICO     → dirección "To" por defecto si un error no trae `to_email`
#                       (campo opcional schema v1.1). Puede ser CSV.
#
# SMTP: reutiliza env vars de enviar_correo (EMISOR_CORREO, PASS_CORREO,
#       SMTP_HOST, SMTP_PORT). ASUNTO/TEXTO heredados pero el script SIEMPRE
#       pasa asunto y cuerpo explícitos a enviar(), de modo que esos defaults
#       no se usan aquí.
#
# Log de control: usa error_system.envio_control (hereda RUTA_CONTROL, LOG_*).
#
# API (callable from Python): `procesar()` corre una pasada y devuelve resumen.
# CLI: `python -m utils.enviar_notificaciones` o `python utils/enviar_notificaciones.py`.
#
# Estado final de cada fichero procesado:
#   - movido a ENVIADOS_DIR con timestamp = mtime tras el move (shutil.move
#     reescribe stat con la hora actual). Borrado en la siguiente pasada si
#     mtime + RETENCION_HORAS*3600 < ahora.

import glob
import os
import shutil
import time
from typing import Optional

from .enviar_correo import EmailWriter
from .error_system import envio_control
from .json_writer import JsonFileWriter


def _carpeta_pendientes() -> str:
    return os.getenv("CARPETA_ERRORES", "./notificaciones/")


def _carpeta_enviados() -> str:
    d = os.getenv("ENVIADOS_DIR")
    if d:
        return d
    return os.path.join(_carpeta_pendientes(), "enviados")


def _retencion_horas() -> int:
    return int(os.getenv("RETENCION_HORAS", "24"))


def _borrar_viejos(enviados_dir: str, retencion_h: int) -> int:
    """Borra ficheros en enviados_dir con mtime anterior a ahora - retencion_h.

    Returns: nº de ficheros borrados.
    """
    if not os.path.isdir(enviados_dir):
        return 0
    cutoff = time.time() - retencion_h * 3600
    borrados = 0
    for f in glob.glob(os.path.join(enviados_dir, "*.json")):
        try:
            if os.stat(f).st_mtime < cutoff:
                os.remove(f)
                borrados += 1
        except OSError as e:
            envio_control(f"no pude borrar {f}: {e}", nivel="WARNING")
    return borrados


def _resolver_destinatarios(err: dict) -> Optional[list]:
    """Devuelve lista de destinatarios para un error, o None si no hay ninguno.

    Prioridad: error.to_email (CSV) → env var EMAIL_GENERICO (CSV).
    """
    to = err.get("to_email") or os.getenv("EMAIL_GENERICO", "")
    if not to:
        return None
    return [r.strip() for r in to.split(",") if r.strip()]


def _procesar_fichero(
    ruta: str,
    m: EmailWriter,
    enviados_dir: str,
) -> dict:
    """Lee un JSON de errores, envía los que tienen notificacion.email=True y lo
    mueve a enviados_dir. Devuelve resumen {enviados, fallidos, sin_dest}.

    Si el fichero no se pudo leer o no tiene errores para email, igualmente se
    mueve a enviados (no dejamos pendientes inválidos pudriéndose en cola).
    """
    resumen = {"enviados": 0, "fallidos": 0, "sin_dest": 0}
    try:
        payload = JsonFileWriter(ruta).read()
    except (OSError, ValueError) as e:
        envio_control(f"no pude leer {ruta}: {e}", nivel="ERROR")
        _mover_a_enviados(ruta, enviados_dir)
        return resumen

    if not payload or not payload.get("errores"):
        envio_control(f"fichero sin errores: {ruta}", nivel="DEBUG")
        _mover_a_enviados(ruta, enviados_dir)
        return resumen

    origen = payload.get("origen", "desconocido")
    for err in payload["errores"]:
        if not isinstance(err, dict):
            continue
        notif = err.get("notificacion", {})
        if not notif.get("email", False):
            continue  # no es para correo

        destinos = _resolver_destinatarios(err)
        if not destinos:
            resumen["sin_dest"] += 1
            envio_control(
                f"error sin destinatario (sin to_email ni EMAIL_GENERICO): {err.get('texto', '')!r}",
                nivel="WARNING",
            )
            continue

        tipo = err.get("tipo", "info")
        texto = err.get("texto", "")
        contexto = err.get("contexto", {})
        asunto = f"[{origen}] {tipo.upper()}: {texto[:50]}"
        cuerpo = (
            f"[{tipo.upper()}] {texto}\n\n"
            f"Origen: {origen}\n"
            f"Contexto: {contexto}"
        )

        # el From es siempre EMISOR_CORREO (quien hace login SMTP); solo mutamos
        # la lista de receptores para este envío.
        m.receptores = destinos
        try:
            m.enviar(asunto, cuerpo)
            resumen["enviados"] += 1
            envio_control(f"enviado a {destinos} — {tipo}: {texto[:40]!r}", nivel="INFO")
        except Exception as e:
            resumen["fallidos"] += 1
            envio_control(f"falló envío a {destinos}: {e}", nivel="ERROR")

    _mover_a_enviados(ruta, enviados_dir)
    return resumen


def _mover_a_enviados(ruta: str, enviados_dir: str) -> None:
    os.makedirs(enviados_dir, exist_ok=True)
    try:
        shutil.move(ruta, os.path.join(enviados_dir, os.path.basename(ruta)))
    except OSError as e:
        envio_control(f"no pude mover {ruta} a enviados: {e}", nivel="ERROR")


def procesar() -> dict:
    """Una pasada: borra viejos, envía pendientes, devuelve resumen total.

    Returns: {borrados, ficheros, enviados, fallidos, sin_dest}
    """
    enviados_dir = _carpeta_enviados()
    pendientes_dir = _carpeta_pendientes()

    borrados = _borrar_viejos(enviados_dir, _retencion_horas())
    if borrados:
        envio_control(f"borrados {borrados} ficheros viejos de enviados/", nivel="INFO")

    pat = os.path.join(pendientes_dir, "errores_*.json")
    ficheros = sorted(glob.glob(pat))
    total = {"borrados": borrados, "ficheros": 0, "enviados": 0, "fallidos": 0, "sin_dest": 0}

    if not ficheros:
        envio_control("sin pendientes", nivel="DEBUG")
        return total

    if not os.getenv("EMISOR_CORREO") or not os.getenv("PASS_CORREO"):
        envio_control(
            "faltan EMISOR_CORREO / PASS_CORREO: no puedo conectar SMTP",
            nivel="ERROR",
        )
        return total

    with EmailWriter() as m:
        m.conectar()
        for ruta in ficheros:
            envio_control(f"procesando {os.path.basename(ruta)}", nivel="DEBUG")
            r = _procesar_fichero(ruta, m, enviados_dir)
            total["ficheros"] += 1
            total["enviados"] += r["enviados"]
            total["fallidos"] += r["fallidos"]
            total["sin_dest"] += r["sin_dest"]

    envio_control(
        f"pasada completa: {total['ficheros']} ficheros, "
        f"{total['enviados']} enviados, {total['fallidos']} fallidos, "
        f"{total['sin_dest']} sin dest",
        nivel="INFO",
    )
    return total


if __name__ == "__main__":
    import sys
    import tempfile
    import importlib

    # --- Self-check sin red: stub de EmailWriter que graba los envíos ---
    with tempfile.TemporaryDirectory() as tmp:
        # salvamos y forzamos env vars del test
        saved = {k: os.environ.get(k) for k in (
            "CARPETA_ERRORES", "ENVIADOS_DIR", "RETENCION_HORAS", "EMAIL_GENERICO",
            "EMISOR_CORREO", "PASS_CORREO", "RECEPTOR_CORREO", "PROYECTO",
            "RUTA_CONTROL", "LOG_NIVEL",
        )}
        # log de control del propio daemon dentro del tmp para no ensuciar el repo
        os.environ["RUTA_CONTROL"] = os.path.join(tmp, "control.log")
        os.environ["CARPETA_ERRORES"] = os.path.join(tmp, "pendientes") + os.sep
        os.environ["ENVIADOS_DIR"] = os.path.join(tmp, "enviados")
        os.environ["RETENCION_HORAS"] = "24"
        os.environ["EMISOR_CORREO"] = "self@check.test"
        os.environ["PASS_CORREO"] = "secret"
        os.environ["EMAIL_GENERICO"] = "generico@x.com"
        os.makedirs(os.environ["CARPETA_ERRORES"], exist_ok=True)

        # stub EmailWriter: captura envíos sin abrir socket
        class _StubEmailWriter:
            def __init__(self):
                self.receptores = []
                self.envios = []  # (receptores, asunto, cuerpo) por enviar()
                self.conectado = False
            def __enter__(self): return self
            def __exit__(self, *a):
                self.conectado = False
            def conectar(self):
                if not os.getenv("EMISOR_CORREO") or not os.getenv("PASS_CORREO"):
                    raise ValueError("faltan creds")
                self.conectado = True
            def enviar(self, asunto=None, cuerpo=None, html=False):
                if not self.conectado:
                    raise RuntimeError("no conectado")
                self.envios.append((list(self.receptores), asunto, cuerpo))

        # parche del símbolo en el módulo bajo test (vía sys.modules lookup)
        import utils.enviar_notificaciones as mod
        original = mod.EmailWriter
        mod.EmailWriter = _StubEmailWriter
        try:
            # 1) sin pendientes — devuelve ceros sin conectar
            assert mod.procesar()["ficheros"] == 0
            assert not os.path.exists(os.environ["ENVIADOS_DIR"])  # no creada si no había nada que mover

            # 2) un JSON con un error email y to_email explícito
            from utils.error_system import nuevo_error
            from utils.json_writer import JsonFileWriter as JW
            err_to = nuevo_error("stop", "fallo crítico", notificar_email=True,
                                 to_email="dest1@x.com,dest2@x.com")
            err_no_email = nuevo_error("info", "solo log", notificar_log=True)
            err_dest_from = nuevo_error("aviso", "fallo leve", notificar_email=True,
                                        from_email="otro@x.com")  # sin to_email: cae a GENERICo
            JW(os.path.join(os.environ["CARPETA_ERRORES"], "errores_20260716_001.json")).write(
                {"schema_version": "1.0", "timestamp_creacion": "t", "origen":"appA", "errores":[err_to, err_no_email, err_dest_from]}
            )

            # otro JSON sin ningún error de email (se debe mover sin enviar)
            JW(os.path.join(os.environ["CARPETA_ERRORES"], "errores_20260716_002.json")).write(
                {"schema_version":"1.0","timestamp_creacion":"t","origen":"appB","errores":[err_no_email]}
            )

            # capturamos los envíos via stub
            stub_instance = _StubEmailWriter()
            mod.EmailWriter = lambda: stub_instance
            res = mod.procesar()
            assert res["ficheros"] == 2, res
            assert res["enviados"] == 2, res
            assert res["fallidos"] == 0, res
            assert res["sin_dest"] == 0, res

            # verificar receptores usados por cada envío
            assert len(stub_instance.envios) == 2, stub_instance.envios
            dests1, asu1, _ = stub_instance.envios[0]
            assert dests1 == ["dest1@x.com", "dest2@x.com"], dests1
            assert asu1.startswith("[appA] STOP:"), asu1
            dests2, asu2, _ = stub_instance.envios[1]
            assert dests2 == ["generico@x.com"], dests2  # no to_email → EMAIL_GENERICO
            assert asu2.startswith("[appA] AVISO:"), asu2

            # todos los pendientes se movieron a enviados/
            assert not glob.glob(os.path.join(os.environ["CARPETA_ERRORES"], "errores_*.json")), "quedaron pendientes"
            enviados = os.listdir(os.environ["ENVIADOS_DIR"])
            assert len(enviados) == 2, enviados

            # 3) error sin destino (sin to_email y EMAIL_GENERICO quitada) → sin_dest cuenta
            os.environ.pop("EMAIL_GENERICO", None)
            err_sin_dest = nuevo_error("stop", "sin a quien avisar", notificar_email=True)
            JW(os.path.join(os.environ["CARPETA_ERRORES"], "errores_20260716_003.json")).write(
                {"schema_version":"1.0","timestamp_creacion":"t","origen":"appC","errores":[err_sin_dest]}
            )
            stub2 = _StubEmailWriter()
            mod.EmailWriter = lambda: stub2
            res = mod.procesar()
            assert res["enviados"] == 0, res
            assert res["sin_dest"] == 1, res
            assert len(stub2.envios) == 0, stub2.envios
            # igual se mueve a enviados (no dejamos pendientes)
            pendientes_restantes = glob.glob(os.path.join(os.environ["CARPETA_ERRORES"], "errores_*.json"))
            assert not pendientes_restantes, pendientes_restantes

            # 4) limpieza de viejos: simulamos un fichero en enviados/ con mtime hace 48h
            viejo = os.path.join(os.environ["ENVIADOS_DIR"], "errores_20260716_003.json")
            old = time.time() - 48 * 3600
            os.utime(viejo, (old, old))
            # ni RETENCION=24 → debe borrarse en la próxima pasada
            mod.EmailWriter = _StubEmailWriter  # no se conectará, no hay pendientes
            res = mod.procesar()
            assert res["borrados"] == 1, res
            assert not os.path.isfile(viejo), "el fichero viejo no se borró"
            # los recientes (>24h) se quedan (como erro_001 y erro_002)
            assert os.path.isfile(os.path.join(os.environ["ENVIADOS_DIR"], "errores_20260716_001.json"))
            assert os.path.isfile(os.path.join(os.environ["ENVIADOS_DIR"], "errores_20260716_002.json"))

            # 5) sin credenciales → se queja y no procesa
            os.environ.pop("EMISOR_CORREO", None)
            JW(os.path.join(os.environ["CARPETA_ERRORES"], "errores_20260716_004.json")).write(
                {"schema_version":"1.0","timestamp_creacion":"t","origen":"appD","errores":[err_to]}
            )
            res = mod.procesar()
            assert res["enviados"] == 0, res
            # el pendiente NO se movió (no se procesó)
            assert glob.glob(os.path.join(os.environ["CARPETA_ERRORES"], "errores_*.json"))

        finally:
            mod.EmailWriter = original
            from .error_system import _reset_logger
            _reset_logger()
            for k, v in saved.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v

    print("enviar_notificaciones v1.0.0 OK")