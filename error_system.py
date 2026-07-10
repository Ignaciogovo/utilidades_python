# utilidades-python:error_system
# Descripción: Sistema unificado de gestión de errores y logs (validación + registro + consulta + trazas de control)
# __version__ = "1.0.0"
#
# Este módulo NO envía correos ni escribe en BBDD. Solo produce ficheros JSON
# con la lista de errores filtrados según el sistema de notificaciones activo.
# Un daemon externo (otro proyecto) será el responsable de leer esos JSON y
# enviar el correo / log / insertar en BBDD según corresponda.
#
# Configuración (variables de entorno):
#   CARPETA_ERRORES  → ruta donde se escriben los JSON de errores. Default: "./errores/"
#   RUTA_CONTROL     → ruta del fichero de trazas de control. Default: "./control.txt"
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

import os
from datetime import datetime
from typing import List, Optional

from json_writer import JsonFileWriter
from text_writer import TextFileWriter


SCHEMA_VERSION = "1.0"
TIPOS_VALIDOS = ("aviso", "stop", "info")
CAMPOS_OBLIGATORIOS = ("tipo", "texto", "timestamp", "dia")


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


def envio_control(texto: str) -> None:
    """Añade una línea de texto al fichero de control (log de trazas).

    El fichero se configura con la env var RUTA_CONTROL (default: "./control.txt").
    Cada llamada añade una línea; un TextFileWriter se crea por llamada (es barato).
    """
    ruta = os.getenv("RUTA_CONTROL", "./control.txt")
    parent = os.path.dirname(ruta)
    if parent:
        os.makedirs(parent, exist_ok=True)
    TextFileWriter(ruta).add_line(texto)


if __name__ == "__main__":
    import tempfile

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

        old_cwd = os.getcwd()
        try:
            os.chdir(tmp)
            envio_control("inicio")
            envio_control("procesando")
            envio_control("fin")
            with open(os.path.join(tmp, "control.txt"), "r") as f:
                contenido = f.read()
            assert contenido == "inicio\nprocesando\nfin", f"control.txt: {contenido!r}"

            ruta_custom = os.path.join(tmp, "subdir", "mi_control.log")
            os.environ["RUTA_CONTROL"] = ruta_custom
            envio_control("con ruta custom")
            with open(ruta_custom, "r") as f:
                contenido2 = f.read()
            assert contenido2 == "con ruta custom"
            del os.environ["RUTA_CONTROL"]
        finally:
            os.chdir(old_cwd)

    print("error_system v1.0.0 OK")
