# utilidades-python:enviar_notificaciones
# Descripción: Daemon one-shot que despacha JSONs de error_system por correo y los
#              archivos en `enviados/`, borrándolos tras N horas.
# __version__ = "1.1.0"
#
# Four-step flow cada ejecución:
#   1) borra viejos de ENVIADOS_DIR (mtime > RETENCION_HORAS)
#   2) lista pendientes CARPETA_ERRORES/errores_*.json
#   3) envía los errores con notificacion.email=True (uno por correo)
#   4) mueve el fichero a ENVIADOS_DIR (marcado como enviado)
#
# Configuración (variables de entorno):
#   CARPETA_ERRORES  → carpeta de pendientes.  Default: "./notificaciones/"
#   ENVIADOS_DIR     → subcarpeta destino.    Default: <CARPETA_ERRORES>enviados
#   RETENCION_HORAS  → horas en enviados/ antes de borrar. Default: "24"
#   EMAIL_GENERICO   → To por defecto si un error no trae to_email. CSV.
#
# SMTP: reutiliza env vars de enviar_correo (EMISOR_CORREO, PASS_CORREO, SMTP_*).
#   RECEPTOR_CORREO no es obligatorio aquí: si no lo seteas, el daemon usa un
#   placeholder (los To reales vienen de to_email/EMAIL_GENERICO por error).
#
# Log: usa error_system.envio_control (hereda RUTA_CONTROL, LOG_NIVEL, ...).
#
# API:  procesar() -> dict  ·  CLI: python -m utils.enviar_notificaciones

import glob
import os
import shutil
import time

from .enviar_correo import EmailWriter
from .error_system import envio_control, _reset_logger
from .json_writer import JsonFileWriter


def borrar_viejos(enviados_dir: str, retencion_h: int) -> int:
    """Borra *.json de enviados_dir con mtime > retencion_h. Devuelve nº borrados."""
    if not os.path.isdir(enviados_dir):
        return 0
    cutoff = time.time() - retencion_h * 3600
    n = 0
    for f in glob.glob(os.path.join(enviados_dir, "*.json")):
        try:
            if os.stat(f).st_mtime < cutoff:
                os.remove(f)
                n += 1
        except OSError as e:
            envio_control(f"no pude borrar {f}: {e}", nivel="ERROR")
    return n


def _iterar_envios(ruta):
    """Lee un JSON de errores y yield'a (to, asunto, cuerpo) por cada error
    con notificacion.email=True y destinatario resolvible. Si no hay ningún
    envío que hacer (no hay email, o no hay destino), simplemente no yield'a
    nada — el llamador debe mover el fichero a enviados/ igual.

    Resolución de To: err.to_email (CSV) → env var EMAIL_GENERICO (CSV).
    Si no hay ninguno, WARNING y skip este error (no yield'a).
    """
    try:
        payload = JsonFileWriter(ruta).read()
    except (OSError, ValueError) as e:
        envio_control(f"no pude leer {ruta}: {e}", nivel="ERROR")
        return

    if not payload or not payload.get("errores"):
        return

    origen = payload.get("origen", "desconocido")
    generico = os.getenv("EMAIL_GENERICO", "")
    for err in payload["errores"]:
        if not isinstance(err, dict):
            continue
        if not err.get("notificacion", {}).get("email", False):
            continue
        to = err.get("to_email") or generico
        destinos = [r.strip() for r in to.split(",") if r.strip()] if to else []
        if not destinos:
            envio_control(
                f"error sin destinatario (sin to_email ni EMAIL_GENERICO): "
                f"{err.get('texto', '')!r}",
                nivel="WARNING",
            )
            continue
        tipo = err.get("tipo", "info")
        texto = err.get("texto", "")
        asunto = f"[{origen}] {tipo.upper()}: {texto[:50]}"
        cuerpo = (
            f"[{tipo.upper()}] {texto}\n\n"
            f"Origen: {origen}\n"
            f"Contexto: {err.get('contexto', {})}"
        )
        yield destinos, asunto, cuerpo


def procesar() -> dict:
    """Una pasada. Devuelve {borrados, enviados, fallidos}."""
    carpeta = os.getenv("CARPETA_ERRORES", "./notificaciones/")
    enviados_dir = os.getenv("ENVIADOS_DIR") or os.path.join(carpeta, "enviados")
    retencion = int(os.getenv("RETENCION_HORAS", "24"))

    borrados = borrar_viejos(enviados_dir, retencion)
    if borrados:
        envio_control(f"borrados {borrados} viejos de enviados/", nivel="INFO")

    pendientes = sorted(glob.glob(os.path.join(carpeta, "errores_*.json")))
    total = {"borrados": borrados, "enviados": 0, "fallidos": 0}

    if not pendientes:
        return total

    if not (os.getenv("EMISOR_CORREO") and os.getenv("PASS_CORREO")):
        envio_control("faltan EMISOR_CORREO / PASS_CORREO: no puedo conectar SMTP", nivel="ERROR")
        return total

    # EmailWriter.__init__ requiere RECEPTOR_CORREO no-vacío para conectar(); los
    # To reales llegan por error (to_email) o EMAIL_GENERICO, y se sobrescriben
    # en m.receptores antes de cada enviar(). Sin setdefault, conectar() revienta.
    os.environ.setdefault("RECEPTOR_CORREO", "noreply@localhost")

    with EmailWriter() as m:
        m.conectar()
        for ruta in pendientes:
            for destinos, asunto, cuerpo in _iterar_envios(ruta):
                m.receptores = destinos
                try:
                    m.enviar(asunto, cuerpo)
                    total["enviados"] += 1
                    envio_control(f"enviado a {destinos} — {asunto}", nivel="INFO")
                except Exception as e:
                    total["fallidos"] += 1
                    envio_control(f"falló envío a {destinos}: {e}", nivel="ERROR")
            # marcar como enviado = mover a enviados/ (se crea sola si hace falta)
            os.makedirs(enviados_dir, exist_ok=True)
            shutil.move(ruta, os.path.join(enviados_dir, os.path.basename(ruta)))

    envio_control(
        f"pasada completa: {len(pendientes)} ficheros, "
        f"{total['enviados']} enviados, {total['fallidos']} fallidos",
        nivel="INFO",
    )
    return total


if __name__ == "__main__":
    """Self-check sin red. Cubre: sin pendientes, envío normal, fallback a
    EMAIL_GENERICO, sin destino, borrado de viejos, sin creds, y el fix del
    RECEPTOR_CORREO (con SMTP real mockeado vía unittest.mock)."""
    import tempfile
    import unittest.mock as mock

    with tempfile.TemporaryDirectory() as tmp:
        # entorno limpio y reproducible
        saved = {k: os.environ.get(k) for k in (
            "CARPETA_ERRORES", "ENVIADOS_DIR", "RETENCION_HORAS", "EMAIL_GENERICO",
            "EMISOR_CORREO", "PASS_CORREO", "RECEPTOR_CORREO", "PROYECTO",
            "RUTA_CONTROL", "LOG_NIVEL",
        )}
        os.environ["RUTA_CONTROL"] = os.path.join(tmp, "control.log")
        os.environ["CARPETA_ERRORES"] = os.path.join(tmp, "p") + os.sep
        os.environ["ENVIADOS_DIR"] = os.path.join(tmp, "e")
        os.environ["RETENCION_HORAS"] = "24"
        os.environ["EMISOR_CORREO"] = "self@check.test"
        os.environ["PASS_CORREO"] = "secret"
        os.environ["EMAIL_GENERICO"] = "generico@x.com"
        os.makedirs(os.environ["CARPETA_ERRORES"], exist_ok=True)

        import utils.enviar_notificaciones as mod
        from utils.error_system import nuevo_error
        from utils.json_writer import JsonFileWriter as JW

        # stub EmailWriter: captura envíos sin abrir socket
        class _Stub:
            def __init__(self): self.receptores = []; self.envios = []; self.on = False
            def __enter__(self): return self
            def __exit__(self, *a): self.on = False
            def conectar(self): self.on = True
            def enviar(self, asunto=None, cuerpo=None, html=False):
                if not self.on: raise RuntimeError("no conectado")
                self.envios.append((list(self.receptores), asunto, cuerpo))

        original = mod.EmailWriter

        def _run_with_stub(stub):
            mod.EmailWriter = lambda: stub
            try:
                return mod.procesar()
            finally:
                mod.EmailWriter = original

        try:
            # 1. sin pendientes — no conecta, devuelve ceros, no crea enviados/
            assert mod.procesar() == {"borrados": 0, "enviados": 0, "fallidos": 0}
            assert not os.path.exists(os.environ["ENVIADOS_DIR"])

            # 2. envío normal: error con to_email explícito + error que cae a genérico
            JW(os.path.join(os.environ["CARPETA_ERRORES"], "errores_1.json")).write({
                "schema_version": "1.0", "timestamp_creacion": "t", "origen": "appA",
                "errores": [
                    nuevo_error("stop", "fallo crítico", notificar_email=True,
                               to_email="d1@x.com,d2@x.com"),
                    nuevo_error("info", "solo log", notificar_log=True),
                    nuevo_error("aviso", "fallo leve", notificar_email=True),  # → generico
                ],
            })
            # JSON sin nada para email — se mueve sin enviar
            JW(os.path.join(os.environ["CARPETA_ERRORES"], "errores_2.json")).write({
                "schema_version": "1.0", "timestamp_creacion": "t", "origen": "appB",
                "errores": [nuevo_error("info", "solo log", notificar_log=True)],
            })
            stub = _Stub()
            res = _run_with_stub(stub)
            assert res == {"borrados": 0, "enviados": 2, "fallidos": 0}, res
            assert len(stub.envios) == 2, stub.envios
            assert stub.envios[0][0] == ["d1@x.com", "d2@x.com"], stub.envios[0]
            assert stub.envios[0][1].startswith("[appA] STOP:"), stub.envios[0]
            assert stub.envios[1][0] == ["generico@x.com"], stub.envios[1]  # no to_email → genérico
            assert stub.envios[1][1].startswith("[appA] AVISO:"), stub.envios[1]
            # todos movidos a enviados/
            assert not glob.glob(os.path.join(os.environ["CARPETA_ERRORES"], "errores_*.json"))
            assert len(os.listdir(os.environ["ENVIADOS_DIR"])) == 2

            # 3. sin destino (sin to_email y EMAIL_GENERICO quitada) → no envía, pero mueve
            os.environ.pop("EMAIL_GENERICO", None)
            JW(os.path.join(os.environ["CARPETA_ERRORES"], "errores_3.json")).write({
                "schema_version": "1.0", "timestamp_creacion": "t", "origen": "appC",
                "errores": [nuevo_error("stop", "sin a quien avisar", notificar_email=True)],
            })
            stub2 = _Stub()
            res = _run_with_stub(stub2)
            assert res["enviados"] == 0, res
            assert len(stub2.envios) == 0, stub2.envios
            assert not glob.glob(os.path.join(os.environ["CARPETA_ERRORES"], "errores_*.json"))
            os.environ["EMAIL_GENERICO"] = "generico@x.com"

            # 4. borrado de viejos: mtime hace 48h → se borra; los recientes se quedan
            viejo = os.path.join(os.environ["ENVIADOS_DIR"], "errores_3.json")
            old = time.time() - 48 * 3600
            os.utime(viejo, (old, old))
            res = mod.procesar()  # sin pendientes, no conecta, solo borra viejos
            assert res["borrados"] == 1, res
            assert not os.path.isfile(viejo)
            assert os.path.isfile(os.path.join(os.environ["ENVIADOS_DIR"], "errores_1.json"))
            assert os.path.isfile(os.path.join(os.environ["ENVIADOS_DIR"], "errores_2.json"))

            # 5. sin creds → se queja y NO mueve pendientes (esperan siguiente pasada)
            os.environ.pop("EMISOR_CORREO", None)
            JW(os.path.join(os.environ["CARPETA_ERRORES"], "errores_4.json")).write({
                "schema_version": "1.0", "timestamp_creacion": "t", "origen": "appD",
                "errores": [nuevo_error("stop", "nuevo fallo", notificar_email=True,
                                       to_email="x@y.com")],
            })
            res = mod.procesar()
            assert res["enviados"] == 0, res
            assert glob.glob(os.path.join(os.environ["CARPETA_ERRORES"], "errores_*.json"))
            os.environ["EMISOR_CORREO"] = "self@check.test"

            # 6. FIX del bug: RECEPTOR_CORREO vacío + SMTP real mockeado → conectar()
            #    NO lanza ValueError porque el setdefault lo rellena con placeholder.
            #    Sin SMTP mockeado no podemos abrir socket real; sin setdefault el
            #    EmailWriter.conectar() real lanza ValueError("Faltan env vars: ...").
            os.environ.pop("RECEPTOR_CORREO", None)
            assert not os.getenv("RECEPTOR_CORREO"), "precondición: vacío en env"

            smtp_calls = {"login_args": None, "sendmail_calls": []}
            class _MockSMTP:
                def __init__(self, host, port): pass
                def ehlo(self): pass
                def starttls(self): pass
                def login(self, user, pwd): smtp_calls["login_args"] = (user, pwd)
                def sendmail(self, frm, to, msg): smtp_calls["sendmail_calls"].append((frm, to, msg))
                def quit(self): pass

            with mock.patch("utils.enviar_correo.smtplib.SMTP", _MockSMTP):
                # usa el EmailWriter REAL (no stub). Sin setdefault, conectar()
                # lanzaría ValueError("Faltan env vars: ... RECEPTOR_CORREO").
                res = mod.procesar()
            # RECEPTOR_CORREO quedó seteado por setdefault, los envíos usaron to_email real
            assert res["enviados"] == 1, res
            assert os.getenv("RECEPTOR_CORREO") == "noreply@localhost", \
                f"setdefault no actuó: {os.getenv('RECEPTOR_CORREO')!r}"
            assert smtp_calls["login_args"] == ("self@check.test", "secret")
            assert len(smtp_calls["sendmail_calls"]) == 1
            frm, to, msg = smtp_calls["sendmail_calls"][0]
            assert frm == "self@check.test", frm
            assert to == ["x@y.com"], to  # el real, no el placeholder
            assert "Subject: [appD] STOP:" in msg
            # el fichero se movió a enviados/
            assert not glob.glob(os.path.join(os.environ["CARPETA_ERRORES"], "errores_*.json"))

        finally:
            mod.EmailWriter = original
            _reset_logger()
            for k, v in saved.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v

    print("enviar_notificaciones v1.1.0 OK")