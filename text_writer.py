# utilidades-python:text_writer
# Descripción: Escritura/append simple de ficheros de texto plano
# __version__ = "1.0.0"
#
# Clase principal: TextFileWriter (estado: guarda filename)
#
# API:
#   writer = TextFileWriter("ruta.txt")
#   writer.write_data("texto")       # crea / sobrescribe
#   writer.add_line("más texto")     # anexa línea (añade \n al inicio si el archivo no está vacío)
#   writer.read_all()                # devuelve el contenido completo como str
#   writer.clear_file()              # vacía el fichero

import os
from typing import Optional


class TextFileWriter:
    def __init__(self, filename: str):
        self.filename = filename

    def _file_exists(self) -> bool:
        if self.filename is None:
            return False
        return os.path.isfile(self.filename)

    def write_data(self, data: str, mode: str = 'w') -> None:
        if self.filename is None:
            return
        with open(self.filename, mode=mode) as text_file:
            if mode == 'a' and self._file_exists():
                text_file.write('\n' + data)
            else:
                text_file.write(data)

    def add_line(self, line: str) -> None:
        self.write_data(line, mode='a')

    def clear_file(self) -> None:
        if self.filename:
            open(self.filename, 'w').close()

    def read_all(self) -> str:
        if not self._file_exists():
            return ""
        with open(self.filename, 'r') as text_file:
            return text_file.read()


if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "test.txt")
        writer = TextFileWriter(path)

        writer.write_data("primera línea")
        writer.add_line("segunda línea")
        writer.add_line("tercera línea")

        content = writer.read_all()
        assert content == "primera línea\nsegunda línea\ntercera línea", f"contenido inesperado: {content!r}"

        writer.clear_file()
        assert writer.read_all() == ""

    print("text_writer v1.0.0 OK")
