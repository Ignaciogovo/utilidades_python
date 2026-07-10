# utilidades-python:json_writer
# Descripción: Escritura/lectura simple de JSON con creación automática de carpetas
# __version__ = "1.0.0"
#
# Clase principal: JsonFileWriter (estado: guarda filepath)
#
# API:
#   w = JsonFileWriter("ruta/data.json")
#   w.write({"a": 1})              # sobrescribe (crea carpetas padre)
#   w.append({"b": 2})             # carga, hace update si dict / extend si list, reescribe
#   w.read()                       # devuelve el JSON o None si no existe / vacío

import json
import os
from typing import Any, Union


class JsonFileWriter:
    def __init__(self, filepath: str):
        self.filepath = filepath

    def _ensure_dir(self) -> None:
        parent = os.path.dirname(self.filepath)
        if parent:
            os.makedirs(parent, exist_ok=True)

    def write(self, data: Any) -> None:
        self._ensure_dir()
        with open(self.filepath, mode='w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write('\n')

    def read(self) -> Any:
        if not os.path.isfile(self.filepath):
            return None
        with open(self.filepath, 'r') as f:
            content = f.read().strip()
        if not content:
            return None
        return json.loads(content)

    def append(self, data: Union[list, dict]) -> None:
        existing = self.read()
        if existing is None:
            self.write(data)
            return
        if isinstance(existing, list) and isinstance(data, list):
            existing.extend(data)
        elif isinstance(existing, dict) and isinstance(data, dict):
            existing.update(data)
        else:
            raise TypeError(
                f"append: tipos incompatibles. existente={type(existing).__name__} "
                f"nuevo={type(data).__name__}. Deben coincidir."
            )
        self.write(existing)


if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "nested", "subdir", "data.json")
        w = JsonFileWriter(path)

        w.write({"a": 1, "b": [1, 2, 3]})
        assert w.read() == {"a": 1, "b": [1, 2, 3]}

        w.append({"c": "nuevo"})
        assert w.read() == {"a": 1, "b": [1, 2, 3], "c": "nuevo"}

        list_path = os.path.join(tmp, "list.json")
        wl = JsonFileWriter(list_path)
        wl.write([1, 2, 3])
        wl.append([4, 5])
        assert wl.read() == [1, 2, 3, 4, 5]

        empty_path = os.path.join(tmp, "empty.json")
        we = JsonFileWriter(empty_path)
        we.append({"x": 1})
        assert we.read() == {"x": 1}

        inexistente = JsonFileWriter(os.path.join(tmp, "no", "existe.json"))
        assert inexistente.read() is None

    print("json_writer v1.0.0 OK")
