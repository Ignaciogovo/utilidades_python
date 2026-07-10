# utilidades-python:time_utils
# Descripción: Utilidades de conversión y validación de fechas (formato compacto YYYYMMDD y extendido YYYY-MM-DD)
# __version__ = "1.0.0"
#
# NOTA sobre formatos:
#   - convert_str_en_fecha / convert_fecha_en_str usan el formato COMPACTO "YYYYMMDD" (8 chars sin separadores)
#   - es_fecha_valida acepta objetos date directamente o strings en formato EXTENDIDO "YYYY-MM-DD"
#   Si necesitas validar un string "YYYYMMDD" pásalo primero por convert_str_en_fecha y captura excepciones.

from datetime import date, datetime


def convert_str_en_fecha(str_fecha: str) -> date:
    """Convierte un string en formato compacto "YYYYMMDD" a objeto date.

    Args:
        str_fecha: string de 8 chars con año(4) + mes(2) + día(2), p.ej. "20260710"

    Returns:
        date correspondiente

    Raises:
        ValueError: si el string no tiene 8 chars o los componentes no son numéricos / válidos
    """
    if not isinstance(str_fecha, str) or len(str_fecha) != 8:
        raise ValueError(f"convert_str_en_fecha: esperaba string de 8 chars, obtuve {str_fecha!r}")
    year = int(str_fecha[:4])
    month = int(str_fecha[4:6])
    day = int(str_fecha[6:8])
    return date(year, month, day)


def convert_fecha_en_str(fecha: date) -> str:
    """Convierte un objeto date a string en formato compacto "YYYYMMDD".

    Args:
        fecha: objeto date

    Returns:
        String de 8 chars, p.ej. "20260710"
    """
    year = fecha.year
    month = str(fecha.month) if fecha.month >= 10 else "0" + str(fecha.month)
    day = str(fecha.day) if fecha.day >= 10 else "0" + str(fecha.day)
    return str(year) + str(month) + str(day)


def es_fecha_valida(fecha) -> bool:
    """Indica si el valor es una fecha válida.

    Acepta:
        - objeto date (de datetime o date)
        - string en formato "YYYY-MM-DD"

    Args:
        fecha: date o str

    Returns:
        bool: True si es válida, False en caso contrario
    """
    try:
        if isinstance(fecha, date):
            return True
        if isinstance(fecha, str):
            datetime.strptime(fecha, "%Y-%m-%d")
            return True
        return False
    except (ValueError, TypeError):
        return False


if __name__ == "__main__":
    assert convert_str_en_fecha("20260710") == date(2026, 7, 10)
    assert convert_str_en_fecha("20000101") == date(2000, 1, 1)

    assert convert_fecha_en_str(date(2026, 7, 10)) == "20260710"
    assert convert_fecha_en_str(date(2000, 1, 1)) == "20000101"
    assert convert_fecha_en_str(date(2026, 12, 31)) == "20261231"

    assert convert_str_en_fecha(convert_fecha_en_str(date(2026, 7, 10))) == date(2026, 7, 10)

    assert es_fecha_valida(date(2026, 7, 10))
    assert es_fecha_valida("2026-07-10")
    assert not es_fecha_valida("2026-13-01")
    assert not es_fecha_valida("no es fecha")
    assert not es_fecha_valida(None)
    assert not es_fecha_valida(12345)
    assert not es_fecha_valida("20260710")
    assert not es_fecha_valida("")

    print("time_utils v1.0.0 OK")
