# utilidades-python:error_manager
# Descripción: Gestión de errores: registra eventos en JSON para consumo por daemon externo
# __version__ = "1.0.0"
#
# Este módulo NO envía correos ni escribe en BBDD. Solo produce un fichero JSON
# con la lista de errores filtrados según el sistema de notificaciones activo.
# Un daemon externo (otro proyecto) será el responsable de leer esos JSON y
# enviar el correo / log / insertar en BBDD según corresponda.
#
# Configuración:
#   Variable de entorno CARPETA_ERRORES (opcional)
#       Ruta donde se escriben los JSON. Default: "./errores/"
#
# Schema JSON v1 que produce este módulo:
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

from error_schema import SCHEMA_VERSION, validate_error
from json_writer import JsonFileWriter


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


def _nombre_fichero() -> str:
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
        if not isinstance(err, dict) or not validate_error(err):
            continue
        notif = err.get("notificacion", {})
        if any(notif.get(canal, False) for canal in sistema if sistema.get(canal, False)):
            errores_filtrados.append(err)

    if not errores_filtrados:
        return None

    carpeta_destino = carpeta or os.getenv("CARPETA_ERRORES", "./errores/")
    os.makedirs(carpeta_destino, exist_ok=True)
    ruta = os.path.join(carpeta_destino, _nombre_fichero())

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

        ruta = registrar_errores(sistema, errores, origen="test_app", carpeta=tmp)
        assert ruta is not None, "debería haber escrito un JSON"
        assert os.path.isfile(ruta)

        payload = JsonFileWriter(ruta).read()
        assert payload["schema_version"] == "1.0"
        assert payload["origen"] == "test_app"
        assert len(payload["errores"]) == 3, f"esperaba 3 errores filtrados, obtuve {len(payload['errores'])}"
        assert all(validate_error(e) for e in payload["errores"])
        assert payload["errores"][0]["contexto"] == {"fichero": "x.csv"}
        assert payload["errores"][0]["notificacion"]["email"] is True

        assert registrar_errores(sistema, [], origen="vacio", carpeta=tmp) is None
        sistema_vacio = {"email": False, "log": False, "bbdd": False}
        assert registrar_errores(sistema_vacio, errores, origen="nada_activo", carpeta=tmp) is None

    print("error_manager v1.0.0 OK")
