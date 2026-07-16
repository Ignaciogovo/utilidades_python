# utilidades-python:error_system
# Descripción: Sistema unificado de gestión de errores y logs (validación + registro + consulta + trazas de control)
# __version__ = "2.0.0"
#
# Este módulo NO envía correos ni escribe en BBDD. Solo produce ficheros JSON
# con la lista de errores filtrados según el sistema de notificaciones activo.
# Un daemon externo (otro proyecto) será el responsable de leer esos JSON y
# enviar el correo / log / insertar en BBDD según corresponda.
#
# Configuración de ERRORES (variables de entorno):
#   CARPETA_ERRORES  → ruta donde se escriben los JSON de errores. Default: "./errores/"
#
# Configuración de LOG (trazas de control, vía envio_control, respaldado por stdlib logging):
#   RUTA_CONTROL         → ruta del fichero de log. Default: "./control.log"
#   LOG_NIVEL            → DEBUG|INFO|WARNING|ERROR|CRITICAL. Filtra lo que se emite. Default: "INFO"
#   LOG_ROTACION_DIAS    → días entre rotaciones (TimedRotatingFileHandler when='D'). Default: "15"
#   LOG_BACKUPS          → nº de ficheros rotated a conservar. 4 × 15 días ≈ 60 días ≈ 2 meses. Default: "4"
#   LOG_FMT              → formato de línea (sintaxis de logging.Formatter). Default: "%(asctime)s | %(levelname)s | %(message)s"
#   LOG_CONSOLE          → "1" para emitir también a stderr, "0" para solo fichero. Default: "0"
#
# API de log (una línea): envio_control("texto")  -> INFO;  envio_control("texto", nivel="ERROR")
#
# Schema JSON v1 que produce este módulo (ver validar_error para el contrato):
# {
#   "schema_version": "1.0",
#   "timestamp_creacion": "2026-07-10T09:30:00",
#   "origen": "nombre_proyecto_o_proceso",
#   "errores": [
#     {
#       "tipo": "aviso | stop | info",
#       "texto": "descripción legible",
#       "timestamp": "2026-07-10T09:25:00",
#       "dia": "2026-07-10",
#       "notificacion": {"email": true, "log": true, "bbdd": false},
#       "contexto": {"cualquier_campo_extra": "..."}
#     }
#   ]
# }

import glob
import logging
import os
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler
from typing import Optional

from .json_writer import JsonFileWriter


SCHEMA_VERSION = "1.0"
TIPOS_VALIDOS = ("aviso", "stop", "info")
CAMPOS_OBLIGATORIOS = ("tipo", "texto", "timestamp", "dia")

# --- Log (envio_control) -------------------------------------------------
_LOG_NIVELES = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}
_LOGGER: Optional[logging.Logger] = None


def _resolve_nivel() -> int:
    return _LOG_NIVELES.get(os.getenv("LOG_NIVEL", "INFO").upper(), logging.INFO)


def _reset_logger() -> None:
    """Solo para tests: descarta el logger configurado y cierra sus handlers."""
    global _LOGGER
    if _LOGGER is not None:
        for h in _LOGGER.handlers:
            h.close()
        _LOGGER.handlers.clear()
    _LOGGER = None


def _get_logger() -> logging.Logger:
    """Devuelve el logger de control configurado una sola vez (idempotente).

    Los handlers (fichero con rotación temporal + opcional stderr) se crean en
    la primera llamada con la configuración de env vars vigente en ese momento.
    El nivel se re-aplica en cada llamada para que LOG_NIVEL cambie en caliente.
    """
    global _LOGGER
    logger = _LOGGER
    if logger is not None:
        logger.setLevel(_resolve_nivel())
        return logger

    ruta = os.getenv("RUTA_CONTROL", "./control.log")
    parent = os.path.dirname(ruta)
    if parent:
        os.makedirs(parent, exist_ok=True)

    fmt = os.getenv("LOG_FMT", "%(asctime)s | %(levelname)s | %(message)s")
    formatter = logging.Formatter(fmt)

    dias = int(os.getenv("LOG_ROTACION_DIAS", "15"))
    backups = int(os.getenv("LOG_BACKUPS", "4"))

    logger = logging.getLogger("envio_control")
    logger.setLevel(_resolve_nivel())
    logger.propagate = False

    if not logger.handlers:
        handler = TimedRotatingFileHandler(
            ruta, when="D", interval=dias, backupCount=backups, encoding="utf-8"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        if os.getenv("LOG_CONSOLE", "0") == "1":
            sh = logging.StreamHandler()
            sh.setFormatter(formatter)
            logger.addHandler(sh)

    _LOGGER = logger
    return logger


def envio_control(texto: str, nivel: str = "INFO") -> None:
    """Escribe una línea de log de control.

    El destino, formato, nivel mínimo y rotación se configuran por env vars
    (ver cabecera del módulo). Centraliza la configuración de logging: los
    programas solo llaman a esta función, sin tocar logger ni handlers.

    Args:
        texto: mensaje a registrar.
        nivel: "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL" (default "INFO").
    """
    lv = _LOG_NIVELES.get(nivel.upper(), logging.INFO)
    _get_logger().log(lv, texto)


def validar_error(error: dict) -> bool:
    """Valida que un dict cumpla el schema v1 de error.

    Returns:
        bool: True si tiene todos los campos obligatorios y tipo válido.
    """
    if not isinstance(error, dict):
        return False
    for campo in CAMPOS_OBLIGATORIOS:
        if campo not in error:
            return False
    if error["tipo"] not in TIPOS_VALIDOS:
        return False
    return True


def nuevo_error(
    tipo: str,
    texto: str,
    notificar_email: bool = False,
    notificar_log: bool = False,
    notificar_bbdd: bool = False,
    contexto: Optional[dict] = None,
) -> dict:
    """Fabrica un dict de error con la forma del schema v1.

    Args:
        tipo: "aviso" | "stop" | "info"
        texto: descripción legible del error
        notificar_*: flags de canales de notificación
        contexto: dict libre con datos específicos del proyecto (jornada, temporada, etc.)

    Returns:
        dict con la estructura del schema v1
    """
    ahora = datetime.now()
    return {
        "tipo": tipo,
        "texto": texto,
        "timestamp": ahora.strftime("%Y-%m-%dT%H:%M:%S"),
        "dia": ahora.strftime("%Y-%m-%d"),
        "notificacion": {
            "email": notificar_email,
            "log": notificar_log,
            "bbdd": notificar_bbdd,
        },
        "contexto": contexto or {},
    }


def fdatos_keys_errores(lista_errores: list, de_key: str) -> list:
    """Devuelve la lista de valores de una clave concreta para cada error.

    Args:
        lista_errores: lista de dicts de error (típicamente creados con nuevo_error)
        de_key: clave a extraer de cada error (p.ej. "tipo", "texto", "timestamp", "dia")

    Returns:
        Lista plana con el valor de la clave en cada error.
        Ejemplo: fdatos_keys_errores([{"tipo":"aviso"},{"tipo":"stop"}], "tipo") -> ["aviso", "stop"]

    Raises:
        KeyError: si algún error no contiene la clave pedida.
    """
    return [err[de_key] for err in lista_errores]


def _nombre_fichero_errores() -> str:
    return f"errores_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"


def registrar_errores(
    sistema: dict,
    errores: list,
    origen: str = "desconocido",
    carpeta: Optional[str] = None,
) -> Optional[str]:
    """Filtra errores según el sistema activo y los escribe a un JSON.

    Args:
        sistema: dict con flags de canales activos, p.ej. {"email": True, "log": True, "bbdd": False}
        errores: lista de dicts de error (típicamente creados con nuevo_error())
        origen: nombre del proyecto o proceso (para trazabilidad en el JSON)
        carpeta: ruta de destino. Si None, usa env var CARPETA_ERRORES o "./errores/"

    Returns:
        Ruta del JSON escrito, o None si no había errores que registrar.
    """
    if not errores:
        return None

    errores_filtrados = []
    for err in errores:
        if not isinstance(err, dict) or not validar_error(err):
            continue
        notif = err.get("notificacion", {})
        if any(notif.get(canal, False) for canal in sistema if sistema.get(canal, False)):
            errores_filtrados.append(err)

    if not errores_filtrados:
        return None

    carpeta_destino = carpeta or os.getenv("CARPETA_ERRORES", "./errores/")
    os.makedirs(carpeta_destino, exist_ok=True)
    ruta = os.path.join(carpeta_destino, _nombre_fichero_errores())

    payload = {
        "schema_version": SCHEMA_VERSION,
        "timestamp_creacion": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "origen": origen,
        "errores": errores_filtrados,
    }

    JsonFileWriter(ruta).write(payload)
    return ruta


if __name__ == "__main__":
    import tempfile

    # --- Tests de errores (registrar_errores, validar_error, nuevo_error) ---
    with tempfile.TemporaryDirectory() as tmp:
        sistema = {"email": True, "log": True, "bbdd": False}
        errores = [
            nuevo_error("aviso", "fallo al escribir CSV", notificar_email=True, notificar_log=True, contexto={"fichero": "x.csv"}),
            nuevo_error("stop", "jornada incompleta", notificar_email=True),
            nuevo_error("info", "proceso terminado", notificar_log=True),
            nuevo_error("info", "ignorado", notificar_email=False, notificar_log=False, notificar_bbdd=False),
            {"tipo": "invalido", "texto": "x", "timestamp": "t", "dia": "d"},
            "no es un dict",
        ]

        assert validar_error(errores[0])
        assert not validar_error({"tipo": "malo", "texto": "x", "timestamp": "t", "dia": "d"})

        tipos = fdatos_keys_errores(errores[:4], "tipo")
        assert tipos == ["aviso", "stop", "info", "info"], tipos

        ruta = registrar_errores(sistema, errores, origen="test_app", carpeta=tmp)
        assert ruta is not None
        assert os.path.isfile(ruta)

        payload = JsonFileWriter(ruta).read()
        assert payload["schema_version"] == "1.0"
        assert payload["origen"] == "test_app"
        assert len(payload["errores"]) == 3
        assert all(validar_error(e) for e in payload["errores"])
        assert payload["errores"][0]["contexto"] == {"fichero": "x.csv"}

        assert registrar_errores(sistema, [], origen="vacio", carpeta=tmp) is None
        sistema_vacio = {"email": False, "log": False, "bbdd": False}
        assert registrar_errores(sistema_vacio, errores, origen="nada_activo", carpeta=tmp) is None

    # --- Tests de log (envio_control: timestamp, niveles, rotación, idempotencia) ---
    saved_env = {k: os.environ.get(k) for k in (
        "RUTA_CONTROL", "LOG_NIVEL", "LOG_ROTACION_DIAS", "LOG_BACKUPS",
        "LOG_FMT", "LOG_CONSOLE",
    )}
    saved_cwd = os.getcwd()
    try:
        with tempfile.TemporaryDirectory() as tmp:
            log_path = os.path.join(tmp, "control.log")
            os.environ["RUTA_CONTROL"] = log_path

            # 1) escritura por defecto (INFO) con timestamp y nivel en la línea
            _reset_logger()
            envio_control("inicio")
            envio_control("procesando")
            log = _get_logger()
            for h in log.handlers:
                h.flush()
            with open(log_path, "r", encoding="utf-8") as f:
                contenido = f.read()
            assert " | INFO | inicio" in contenido, contenido
            assert " | INFO | procesando" in contenido, contenido
            assert contenido.count("\n") == 2, contenido

            # 2) niveles y filtrado: LOG_NIVEL=WARNING descarta INFO y DEBUG
            _reset_logger()
            os.environ["LOG_NIVEL"] = "WARNING"
            for h in _get_logger().handlers:
                pass
            envio_control("debug oculto", nivel="DEBUG")
            envio_control("info oculto", nivel="INFO")
            envio_control("visible warning", nivel="WARNING")
            envio_control("visible error", nivel="ERROR")
            log = _get_logger()
            for h in log.handlers:
                h.flush()
            with open(log_path, "r", encoding="utf-8") as f:
                cont = f.read()
            assert "debug oculto" not in cont, cont
            assert "info oculto" not in cont, cont
            assert " | WARNING | visible warning" in cont, cont
            assert " | ERROR | visible error" in cont, cont

            # 3) idempotencia: una segunda llamada a _get_logger no duplica handlers
            n_handlers_antes = len(_get_logger().handlers)
            _get_logger()
            _get_logger()
            assert len(_get_logger().handlers) == n_handlers_antes, "se duplicaron handlers"

            # 4) rotación temporal: doRollover genera un backup y reabre el activo
            os.environ["LOG_NIVEL"] = "INFO"
            _reset_logger()
            envio_control("pre-rotacion")
            log = _get_logger()
            for h in log.handlers:
                h.flush()
            file_handler = next(h for h in log.handlers if isinstance(h, TimedRotatingFileHandler))
            file_handler.doRollover()
            backups = glob.glob(os.path.join(tmp, "control.log.*"))
            assert backups, f"no se generó backup de rotación: {os.listdir(tmp)}"
            assert os.path.isfile(log_path), "el fichero activo debe reabrirse tras rotar"

            _reset_logger()
    finally:
        _reset_logger()
        os.chdir(saved_cwd)
        for k, v in saved_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    print("error_system v2.0.0 OK")