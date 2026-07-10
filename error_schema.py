# utilidades-python:error_schema
# Descripción: Constantes y validación del schema JSON de errores v1
# __version__ = "1.0.0"
#
# Schema JSON v1 (ver docstring de error_manager para el payload completo):
# {
#   "tipo": "aviso" | "stop" | "info",
#   "texto": "descripción legible",
#   "timestamp": "2026-07-10T09:25:00",
#   "dia": "2026-07-10",
#   "notificacion": {"email": bool, "log": bool, "bbdd": bool},
#   "contexto": { ...campos libres del proyecto... }
# }

SCHEMA_VERSION = "1.0"
TIPOS_VALIDOS = ("aviso", "stop", "info")
CAMPOS_OBLIGATORIOS = ("tipo", "texto", "timestamp", "dia")


def validate_error(error: dict) -> bool:
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


if __name__ == "__main__":
    base = {
        "tipo": "aviso",
        "texto": "test",
        "timestamp": "2026-07-10T09:30:00",
        "dia": "2026-07-10",
    }
    assert validate_error(base)
    assert validate_error({**base, "tipo": "info"})
    assert validate_error({**base, "tipo": "stop"})

    assert not validate_error({k: v for k, v in base.items() if k != "tipo"})
    assert not validate_error({**base, "tipo": "warning"})
    assert not validate_error("string")
    assert not validate_error(None)

    assert validate_error({**base, "notificacion": {"email": True}, "contexto": {"k": 1}})

    print("error_schema v1.0.0 OK")
