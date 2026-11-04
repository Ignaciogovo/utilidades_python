# extensiones-python:check_updates
# Descripción: Compara versiones de extensiones entre el repo origen y una copia destino
# __version__ = "1.0.0"
#
# Uso:
#   python extensiones/check_updates.py <origen> <destino>
#
# <origen> y <destino> admiten dos formas (la misma en ambos lados):
#   - Las carpetas extensiones/ (compara todas las extensiones que contengan)
#   - Las carpetas concretas de una extensión (compara solo esa)
#
# Cada extensión versiona su Dockerfile con la cabecera:
#   # extensiones-python:nombre
#   # __version__ = "X.Y.Z"
#
# Ejemplos:
#   python extensiones/check_updates.py /workspace/utilidades_python/extensiones/ ~/work/mi_proyecto/extensiones/
#   python extensiones/check_updates.py /workspace/utilidades_python/extensiones/log_viewer/ ~/work/mi_proyecto/log_viewer/
#
# Exit codes:
#   0 = todo actualizado
#   1 = hay desactualizados, faltan extensiones o no tienen __version__
#   2 = error de argumentos / rutas / modos mezclados
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


def _tiene_dockerfile(d: str) -> bool:
    return os.path.isfile(os.path.join(d, "Dockerfile"))


def find_extensions(parent_dir: str) -> Dict[str, str]:
    """Subcarpetas de parent con Dockerfile versionado -> {nombre: version}."""
    exts = {}
    for entry in os.listdir(parent_dir):
        full = os.path.join(parent_dir, entry)
        if not os.path.isdir(full) or not _tiene_dockerfile(full):
            continue
        v = extract_version(os.path.join(full, "Dockerfile"))
        if v:
            exts[entry] = v
    return exts


def _fila_version(nombre: str, sv: str, dv: str) -> Tuple[str, str, str, str]:
    if parse_version(dv) < parse_version(sv):
        return (nombre, "DESACTUALIZADO", sv, dv)
    if parse_version(dv) > parse_version(sv):
        return (nombre, "MAS_NUEVO_EN_DESTINO", sv, dv)
    return (nombre, "OK", sv, dv)


def compare(source_dir: str, dest_dir: str) -> List[Tuple[str, str, str, str]]:
    if not os.path.isdir(source_dir):
        raise FileNotFoundError(f"origen no existe: {source_dir}")
    if not os.path.isdir(dest_dir):
        raise FileNotFoundError(f"destino no existe: {dest_dir}")

    src_single = _tiene_dockerfile(source_dir)
    dst_single = _tiene_dockerfile(dest_dir)
    if src_single != dst_single:
        raise ValueError(
            "modos mezclados: un lado es una extension (tiene Dockerfile) y el otro no. "
            "Pasa las carpetas extensiones/ en ambos lados, o la carpeta concreta de "
            "la misma extension en ambos lados."
        )

    if src_single:
        nombre = os.path.basename(os.path.normpath(source_dir))
        sv = extract_version(os.path.join(source_dir, "Dockerfile"))
        dv = extract_version(os.path.join(dest_dir, "Dockerfile"))
        if sv is None or dv is None:
            return [(nombre, "SIN_VERSION", sv or "—", dv or "—")]
        return [_fila_version(nombre, sv, dv)]

    rows = []
    for nombre, sv in sorted(find_extensions(source_dir).items()):
        dest_path = os.path.join(dest_dir, nombre)
        if not os.path.isdir(dest_path):
            rows.append((nombre, "FALTA_EN_DESTINO", sv, "—"))
            continue
        dv = extract_version(os.path.join(dest_path, "Dockerfile"))
        if dv is None:
            rows.append((nombre, "SIN_VERSION", sv, "—"))
            continue
        rows.append(_fila_version(nombre, sv, dv))
    return rows


def print_report(source_dir: str, dest_dir: str, rows: List[Tuple[str, str, str, str]]) -> int:
    print(f"\nOrigen:  {source_dir}")
    print(f"Destino: {dest_dir}\n")

    if not rows:
        print("(no se encontraron extensiones versionadas en el origen)")
        return 0

    name_w = max(len(r[0]) for r in rows)
    name_w = max(name_w, len("extension"))
    header = f"  {'extension':<{name_w}}  {'origen':<10}  {'destino':<10}  estado"
    print(header)
    print("  " + "-" * (len(header) - 2))

    counts = {"OK": 0, "DESACTUALIZADO": 0, "FALTA_EN_DESTINO": 0, "MAS_NUEVO_EN_DESTINO": 0, "SIN_VERSION": 0}
    for nombre, status, sv, dv in rows:
        print(f"  {nombre:<{name_w}}  {sv:<10}  {dv:<10}  {status}")
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
    except (FileNotFoundError, ValueError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    return print_report(source_dir, dest_dir, rows)


def self_check() -> None:
    import tempfile

    def crear(d: str, version: Optional[str]) -> None:
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "Dockerfile"), "w") as f:
            f.write(f"# extensiones-python:{os.path.basename(d)}\n")
            if version:
                f.write(f'# __version__ = "{version}"\n')
            f.write("FROM python:3-slim\n")

    with tempfile.TemporaryDirectory() as tmp:
        # modo contenedor: desactualizado + falta + sin version + mas nuevo
        orig = os.path.join(tmp, "orig")
        dest = os.path.join(tmp, "dest")
        os.makedirs(orig)
        os.makedirs(dest)
        crear(os.path.join(orig, "ext_a"), "1.0.0")
        crear(os.path.join(orig, "ext_b"), "1.1.0")
        crear(os.path.join(orig, "ext_c"), "1.0.0")
        crear(os.path.join(orig, "ext_d"), "1.0.0")
        crear(os.path.join(dest, "ext_a"), "0.9.0")
        crear(os.path.join(dest, "ext_c"), None)      # Dockerfile sin __version__
        crear(os.path.join(dest, "ext_d"), "2.0.0")
        rows = compare(orig, dest)
        estados = {r[0]: r[1] for r in rows}
        assert estados["ext_a"] == "DESACTUALIZADO", estados
        assert estados["ext_b"] == "FALTA_EN_DESTINO", estados
        assert estados["ext_c"] == "SIN_VERSION", estados
        assert estados["ext_d"] == "MAS_NUEVO_EN_DESTINO", estados
        assert print_report(orig, dest, rows) == 1

        # modo contenedor: todo OK
        orig2 = os.path.join(tmp, "orig2")
        dest2 = os.path.join(tmp, "dest2")
        os.makedirs(orig2)
        os.makedirs(dest2)
        crear(os.path.join(orig2, "log_viewer"), "1.0.0")
        crear(os.path.join(dest2, "log_viewer"), "1.0.0")
        rows2 = compare(orig2, dest2)
        assert rows2 == [("log_viewer", "OK", "1.0.0", "1.0.0")], rows2
        assert print_report(orig2, dest2, rows2) == 0

        # modo extension unica: desactualizado
        orig3 = os.path.join(tmp, "orig3", "enviar_notificaciones")
        dest3 = os.path.join(tmp, "dest3", "enviar_notificaciones")
        crear(orig3, "2.0.0")
        crear(dest3, "1.0.0")
        rows3 = compare(orig3, dest3)
        assert rows3 == [("enviar_notificaciones", "DESACTUALIZADO", "2.0.0", "1.0.0")], rows3
        assert print_report(orig3, dest3, rows3) == 1

        # modo extension unica: OK
        orig4 = os.path.join(tmp, "orig4")
        dest4 = os.path.join(tmp, "dest4")
        crear(orig4, "1.0.0")
        crear(dest4, "1.0.0")
        rows4 = compare(orig4, dest4)
        assert rows4[0][1] == "OK", rows4
        assert print_report(orig4, dest4, rows4) == 0

        # modo extension unica: origen sin __version__
        orig5 = os.path.join(tmp, "orig5", "sinver")
        dest5 = os.path.join(tmp, "dest5", "sinver")
        crear(orig5, None)
        crear(dest5, "1.0.0")
        rows5 = compare(orig5, dest5)
        assert rows5 == [("sinver", "SIN_VERSION", "—", "1.0.0")], rows5

        # modos mezclados -> exit 2
        assert main(["check_updates.py", orig, dest4]) == 2
        assert main(["check_updates.py", orig4, dest]) == 2

    print("check_updates (extensiones) v1.0.0 OK")


if __name__ == "__main__":
    if len(sys.argv) == 3:
        sys.exit(main(sys.argv))
    else:
        self_check()
