# utilidades-python:text_writer
# Descripción: Escritura/append simple de ficheros de texto plano
# __version__ = "1.0.1"
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
        needs_leading_newline = (
            mode == 'a'
            and self._file_exists()
            and os.path.getsize(self.filename) > 0
        )
        with open(self.filename, mode=mode) as text_file:
            if needs_leading_newline:
                text_file.write('\n')
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

        # verifica que el primer add_line sobre archivo nuevo no añade \n espurio
        path2 = os.path.join(tmp, "fresh.txt")
        w2 = TextFileWriter(path2)
        w2.add_line("primera y única")
        assert w2.read_all() == "primera y única", f"fresh: {w2.read_all()!r}"

        writer.clear_file()
        assert writer.read_all() == ""

    print("text_writer v1.0.1 OK")
