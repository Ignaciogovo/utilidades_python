# utilidades-python:csv_writer
# Descripción: Escritura/lectura simple de CSV con control de cabeceras y modos
# __version__ = "1.0.0"
#
# Clase principal: CSVWriter (estado: guarda filename + headers)
# Wrapper de un solo uso: exportar_csv (decide sobrescribir vs anexar)
#
# API:
#   writer = CSVWriter("ruta.csv", ["col1", "col2"])
#   writer.write_data(["v1", "v2"])          # crea / sobrescribe, escribe cabecera + fila
#   writer.add_row(["v3", "v4"])             # anexa fila
#   writer.read_all()                        # lista de dicts {col1: v1, ...}
#   writer.is_empty_csv()                    # bool
#   writer.clear_file()                      # vacía el fichero
#
#   exportar_csv("ruta.csv", ["v1"], cabecera=["c1"], modo="sobrescribir") -> bool
#   exportar_csv("ruta.csv", ["v2"], cabecera=["c1"], modo="anexar")        -> bool

import csv
import os
from typing import Any, Dict, List, Optional


class CSVWriter:
    def __init__(self, filename: str, headers: Optional[List[str]] = None):
        self.filename = filename
        self.headers = headers or []

    def _file_exists(self) -> bool:
        if self.filename is None:
            return False
        return os.path.isfile(self.filename)

    def write_data(self, data: List[Any], mode: str = 'w') -> None:
        if self.filename is None:
            return
        with open(self.filename, mode=mode, newline='') as csv_file:
            writer = csv.writer(csv_file)
            if mode == 'w' or not self._file_exists():
                if self.headers:
                    writer.writerow(self.headers)
            writer.writerow(data)

    def add_row(self, row: List[Any]) -> None:
        self.write_data(row, mode='a')

    def is_empty_csv(self) -> bool:
        if not self._file_exists():
            return True
        with open(self.filename, 'r', newline='') as file:
            for _ in csv.reader(file):
                return False
        return True

    def clear_file(self) -> None:
        if self.filename:
            open(self.filename, 'w').close()

    def read_all(self) -> List[Dict[str, Any]]:
        if not self._file_exists():
            return []
        with open(self.filename, 'r', newline='') as file:
            return list(csv.DictReader(file))


def exportar_csv(
    filename: str,
    datos: List[Any],
    cabecera: Optional[List[str]] = None,
    modo: str = "sobrescribir",
) -> bool:
    if not datos or not filename:
        return False
    writer = CSVWriter(filename, cabecera)
    if writer._file_exists() and modo == "anexar" and not writer.is_empty_csv():
        writer.add_row(datos)
    else:
        writer.write_data(datos, mode='w')
    return True


if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "test.csv")
        cabecera = ["fecha", "valor", "estado"]

        assert exportar_csv(path, ["2026-07-10", "42", "ok"], cabecera, "sobrescribir")
        assert exportar_csv(path, ["2026-07-10", "99", "warn"], cabecera, "anexar")

        reader = CSVWriter(path, cabecera)
        rows = reader.read_all()
        assert rows == [
            {"fecha": "2026-07-10", "valor": "42", "estado": "ok"},
            {"fecha": "2026-07-10", "valor": "99", "estado": "warn"},
        ], f"rows inesperadas: {rows}"
        assert not reader.is_empty_csv()

        reader.clear_file()
        assert reader.is_empty_csv()

        assert not exportar_csv("", ["x"], cabecera)
        assert not exportar_csv(path, [], cabecera)

    print("csv_writer v1.0.0 OK")
