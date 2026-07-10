# utilidades-python:check_updates
# Descripción: Compara versiones de utilidades entre el repo origen y un proyecto destino
# __version__ = "1.0.0"
#
# Uso:
#   python check_updates.py <directorio_origen> <directorio_destino>
#
# Ejemplo:
#   python check_updates.py /workspace/utilidades_python/ ~/work/mi_proyecto/utils/
#
# Para chequear varios proyectos de una vez:
#   for proj in ~/work/*/; do
#     python check_updates.py /workspace/utilidades_python/ "$proj/utils/"
#   done
#
# Exit codes:
#   0 = todo actualizado
#   1 = hay desactualizados, faltan utilidades o no tienen __version__
#   2 = error de argumentos / rutas no existen
#
# Sin argumentos: corre el self-check.

import os
import re
import sys
from typing import Dict, List, Optional, Tuple


VERSION_RE = re.compile(r'__version__\s*=\s*["\']([\d.]+)["\']')


def parse_version(v: str) -> Tuple[int, ...]:
    return tuple(int(x) for x in v.split("."))


def extract_version(filepath: str) -> Optional[str]:
    try:
        with open(filepath, 'r') as f:
            for _ in range(10):
                line = f.readline()
                if not line:
                    break
                m = VERSION_RE.search(line)
                if m:
                    return m.group(1)
    except OSError:
        return None
    return None


def find_utilities(source_dir: str) -> Dict[str, str]:
    utils = {}
    for entry in os.listdir(source_dir):
        if not entry.endswith('.py') or entry == 'check_updates.py':
            continue
        full = os.path.join(source_dir, entry)
        if not os.path.isfile(full):
            continue
        v = extract_version(full)
        if v:
            utils[entry] = v
    return utils


def compare(source_dir: str, dest_dir: str) -> List[Tuple[str, str, str, str]]:
    if not os.path.isdir(source_dir):
        raise FileNotFoundError(f"origen no existe: {source_dir}")
    if not os.path.isdir(dest_dir):
        raise FileNotFoundError(f"destino no existe: {dest_dir}")

    source_utils = find_utilities(source_dir)
    rows = []
    for filename, source_v in sorted(source_utils.items()):
        dest_path = os.path.join(dest_dir, filename)
        if not os.path.isfile(dest_path):
            rows.append((filename, "FALTA_EN_DESTINO", source_v, "—"))
            continue
        dest_v = extract_version(dest_path)
        if dest_v is None:
            rows.append((filename, "SIN_VERSION", source_v, "—"))
            continue
        if parse_version(dest_v) < parse_version(source_v):
            rows.append((filename, "DESACTUALIZADO", source_v, dest_v))
        elif parse_version(dest_v) > parse_version(source_v):
            rows.append((filename, "MAS_NUEVO_EN_DESTINO", source_v, dest_v))
        else:
            rows.append((filename, "OK", source_v, dest_v))
    return rows


def print_report(source_dir: str, dest_dir: str, rows: List[Tuple[str, str, str, str]]) -> int:
    print(f"\nOrigen:  {source_dir}")
    print(f"Destino: {dest_dir}\n")

    if not rows:
        print("(no se encontraron utilidades versionadas en el origen)")
        return 0

    name_w = max(len(r[0]) for r in rows)
    name_w = max(name_w, len("archivo"))
    header = f"  {'archivo':<{name_w}}  {'origen':<10}  {'destino':<10}  estado"
    print(header)
    print("  " + "-" * (len(header) - 2))

    counts = {"OK": 0, "DESACTUALIZADO": 0, "FALTA_EN_DESTINO": 0, "MAS_NUEVO_EN_DESTINO": 0, "SIN_VERSION": 0}
    for filename, status, sv, dv in rows:
        print(f"  {filename:<{name_w}}  {sv:<10}  {dv:<10}  {status}")
        counts[status] = counts.get(status, 0) + 1

    print(
        f"\nResumen: {counts['OK']} OK, {counts['DESACTUALIZADO']} desactualizados, "
        f"{counts['FALTA_EN_DESTINO']} faltan, {counts['MAS_NUEVO_EN_DESTINO']} mas nuevos en destino, "
        f"{counts['SIN_VERSION']} sin version"
    )

    hay_problemas = counts["DESACTUALIZADO"] > 0 or counts["FALTA_EN_DESTINO"] > 0 or counts["SIN_VERSION"] > 0
    return 1 if hay_problemas else 0


def main(argv: List[str]) -> int:
    if len(argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2

    source_dir = os.path.abspath(argv[1])
    dest_dir = os.path.abspath(argv[2])

    try:
        rows = compare(source_dir, dest_dir)
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    return print_report(source_dir, dest_dir, rows)


def self_check() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        orig_dir = os.path.join(tmp, "orig")
        dest_dir = os.path.join(tmp, "dest")
        os.makedirs(orig_dir)
        os.makedirs(dest_dir)

        with open(os.path.join(orig_dir, "vieja.py"), "w") as f:
            f.write('# utilidades-python:vieja\n# __version__ = "1.0.0"\n')
        with open(os.path.join(orig_dir, "nueva.py"), "w") as f:
            f.write('# utilidades-python:nueva\n# __version__ = "1.1.0"\n')

        with open(os.path.join(dest_dir, "vieja.py"), "w") as f:
            f.write('# utilidades-python:vieja\n# __version__ = "0.9.0"\n')

        rows = compare(orig_dir, dest_dir)
        statuses = {r[0]: r[1] for r in rows}
        assert statuses["vieja.py"] == "DESACTUALIZADO", statuses
        assert statuses["nueva.py"] == "FALTA_EN_DESTINO", statuses
        assert len(rows) == 2

        orig_dir2 = os.path.join(tmp, "orig2")
        dest_dir2 = os.path.join(tmp, "dest2")
        os.makedirs(orig_dir2)
        os.makedirs(dest_dir2)
        with open(os.path.join(orig_dir2, "x.py"), "w") as f:
            f.write('# __version__ = "1.0.0"\n')
        with open(os.path.join(dest_dir2, "x.py"), "w") as f:
            f.write('# __version__ = "1.0.0"\n')
        rows2 = compare(orig_dir2, dest_dir2)
        assert rows2[0][1] == "OK"
        assert print_report(orig_dir2, dest_dir2, rows2) == 0

        orig_dir3 = os.path.join(tmp, "orig3")
        dest_dir3 = os.path.join(tmp, "dest3")
        os.makedirs(orig_dir3)
        os.makedirs(dest_dir3)
        with open(os.path.join(orig_dir3, "y.py"), "w") as f:
            f.write('# __version__ = "2.0.0"\n')
        with open(os.path.join(dest_dir3, "y.py"), "w") as f:
            f.write('# __version__ = "1.0.0"\n')
        rows3 = compare(orig_dir3, dest_dir3)
        assert rows3[0][1] == "DESACTUALIZADO"
        assert print_report(orig_dir3, dest_dir3, rows3) == 1

    print("check_updates v1.0.0 OK")


if __name__ == "__main__":
    if len(sys.argv) == 3:
        sys.exit(main(sys.argv))
    else:
        self_check()
