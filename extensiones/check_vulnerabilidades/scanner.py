"""Escanea imágenes locales y convierte los hallazgos en notificaciones JSON."""

import fnmatch
import http.client
import json
import os
import socket
import subprocess
import sys
from collections import Counter
from datetime import datetime
from typing import Any

from utils.error_system import envio_control, nuevo_error, registrar_errores


DOCKER_SOCKET = "/var/run/docker.sock"
TRIVY = "/usr/local/bin/trivy"


class UnixHTTPConnection(http.client.HTTPConnection):
    def __init__(self, socket_path: str):
        super().__init__("localhost")
        self.socket_path = socket_path

    def connect(self) -> None:
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.connect(self.socket_path)


def docker_get(path: str) -> Any:
    connection = UnixHTTPConnection(DOCKER_SOCKET)
    try:
        connection.request("GET", path, headers={"Host": "localhost"})
        response = connection.getresponse()
        body = response.read().decode()
        if response.status >= 400:
            raise RuntimeError(f"Docker API {response.status}: {body[:300]}")
        return json.loads(body)
    finally:
        connection.close()


def docker_images() -> list[dict[str, Any]]:
    version = docker_get("/version").get("ApiVersion", "1.41")
    return docker_get(f"/v{version}/images/json?all=1")


def docker_containers() -> list[dict[str, Any]]:
    version = docker_get("/version").get("ApiVersion", "1.41")
    all_containers = "1" if verdad(os.getenv("INCLUIR_DETENIDOS", "0")) else "0"
    return docker_get(f"/v{version}/containers/json?all={all_containers}")


def valores(texto: str) -> list[str]:
    return [valor.strip() for valor in texto.replace("\n", ",").split(",") if valor.strip()]


def verdad(texto: str) -> bool:
    return texto.strip().lower() in {"1", "true", "yes", "si", "sí"}


def referencias(imagen: dict[str, Any]) -> list[str]:
    tags = [tag for tag in imagen.get("RepoTags") or [] if tag and not tag.startswith("<none>")]
    digests = [digest for digest in imagen.get("RepoDigests") or [] if digest and not digest.startswith("<none>")]
    return tags + digests


def etiquetas(imagen: dict[str, Any]) -> list[str]:
    return [tag for tag in imagen.get("RepoTags") or [] if tag and not tag.startswith("<none>")]


def coincide(imagen: dict[str, Any], filtros: list[str]) -> bool:
    refs = referencias(imagen)
    image_id = imagen.get("Id", "")
    for filtro in filtros:
        if filtro in {imagen.get("Id"), image_id.removeprefix("sha256:")}:  # noqa: SIM118
            return True
        if any(
            fnmatch.fnmatch(ref, filtro)
            or fnmatch.fnmatch(ref.split("@", 1)[0], filtro)
            or filtro in ref
            for ref in refs
        ):
            return True
    return False


def seleccionar_imagenes() -> list[dict[str, Any]]:
    imagenes = docker_images()
    filtros = valores(os.getenv("IMAGENES", "TODAS"))
    todas = not filtros or any(filtro.upper() in {"TODAS", "ALL", "*"} for filtro in filtros)
    incluir_dangling = verdad(os.getenv("INCLUIR_DANGLING", "0"))
    solo_en_uso = verdad(os.getenv("SOLO_EN_USO", "1"))
    en_uso = {container.get("ImageID") for container in docker_containers()} if solo_en_uso else set()
    seleccionadas = []
    vistas = set()

    for imagen in imagenes:
        image_id = imagen.get("Id", "")
        if not image_id or image_id in vistas:
            continue
        if solo_en_uso and image_id not in en_uso:
            continue
        if not incluir_dangling and not etiquetas(imagen):
            continue
        if not todas and not coincide(imagen, filtros):
            continue
        vistas.add(image_id)
        seleccionadas.append(imagen)

    if not seleccionadas:
        raise RuntimeError("No hay imágenes locales que coincidan con la configuración")
    return seleccionadas


def cargar_estado() -> dict[str, str]:
    ruta = os.getenv("ESTADO_FILE", "/app/estado/estado.json")
    try:
        with open(ruta, encoding="utf-8") as archivo:
            estado = json.load(archivo)
        return estado if isinstance(estado, dict) else {}
    except FileNotFoundError:
        return {}
    except (OSError, json.JSONDecodeError) as error:
        envio_control(f"no pude leer el estado: {error}; empezaré sin historial", "WARNING")
        return {}


def guardar_estado(estado: dict[str, str]) -> None:
    ruta = os.getenv("ESTADO_FILE", "/app/estado/estado.json")
    carpeta = os.path.dirname(ruta)
    if carpeta:
        os.makedirs(carpeta, exist_ok=True)
    temporal = f"{ruta}.tmp"
    with open(temporal, "w", encoding="utf-8") as archivo:
        json.dump(estado, archivo, ensure_ascii=False, indent=2)
    os.replace(temporal, ruta)


def clave_hallazgo(hallazgo: dict[str, Any]) -> str:
    return "|".join([
        hallazgo["id_imagen"],
        hallazgo.get("VulnerabilityID", "sin-CVE"),
        hallazgo.get("PkgName", "paquete desconocido"),
        hallazgo.get("InstalledVersion", "desconocida"),
    ])


def escanear(imagen: dict[str, Any]) -> list[dict[str, Any]]:
    image_id = imagen["Id"]
    comando = [TRIVY, "image", "--scanners", "vuln", "--format", "json", "--exit-code", "0"]
    severidades = os.getenv("SEVERIDADES", "HIGH,CRITICAL").strip()
    if severidades:
        comando.extend(["--severity", severidades])
    if verdad(os.getenv("IGNORAR_SIN_CORREGIR", "1")):
        comando.append("--ignore-unfixed")
    comando.append(image_id)

    proceso = subprocess.run(comando, capture_output=True, text=True, timeout=600)
    if proceso.returncode:
        raise RuntimeError(proceso.stderr.strip()[-1000:] or "Trivy no pudo analizar la imagen")
    try:
        informe = json.loads(proceso.stdout or "{}")
    except json.JSONDecodeError as error:
        raise RuntimeError(f"Trivy devolvió JSON inválido: {error}") from error

    hallazgos = []
    for resultado in informe.get("Results", []):
        for vulnerabilidad in resultado.get("Vulnerabilities") or []:
            hallazgos.append({
                "imagen": referencias(imagen) or [image_id],
                "id_imagen": image_id,
                "objetivo": resultado.get("Target", ""),
                **vulnerabilidad,
            })
    return hallazgos


def error_resumen(
    imagen: dict[str, Any], hallazgos: list[dict[str, Any]], nuevas: int
) -> dict[str, Any]:
    por_severidad = Counter(hallazgo.get("Severity", "UNKNOWN") for hallazgo in hallazgos)
    imagenes = referencias(imagen) or [imagen["Id"]]
    nombre = ", ".join(imagenes)
    resumen = ", ".join(f"{nivel}: {total}" for nivel, total in sorted(por_severidad.items()))
    comando = f"docker image rm {imagen['Id']}"
    texto = f"{nombre}: {len(hallazgos)} vulnerabilidades ({resumen}; {nuevas} nuevas). Limpieza: {comando}"
    return nuevo_error(
        "stop" if por_severidad.get("CRITICAL") else "aviso",
        texto,
        notificar_email=True,
        notificar_log=True,
        contexto={
            "imagen": imagenes,
            "id_imagen": imagen["Id"],
            "total": len(hallazgos),
            "nuevas": nuevas,
            "por_severidad": dict(por_severidad),
            "comando_eliminar": comando,
        },
    )


def error_fallo(texto: str, contexto: dict[str, Any] | None = None) -> dict[str, Any]:
    return nuevo_error(
        "stop",
        texto,
        notificar_email=True,
        notificar_log=True,
        contexto=contexto or {},
    )


def auto_check() -> None:
    assert valores("a,b\nc") == ["a", "b", "c"]
    assert verdad("sí") and not verdad("0")
    imagen = {"Id": "sha256:abc", "RepoTags": ["demo:latest"], "RepoDigests": []}
    assert referencias(imagen) == ["demo:latest"]
    assert coincide(imagen, ["demo:*"])
    resumen = error_resumen(
        imagen,
        [{"Severity": "HIGH"}, {"Severity": "CRITICAL"}],
        2,
    )
    assert resumen["notificacion"]["email"]
    assert resumen["contexto"]["total"] == 2
    assert "docker image rm sha256:abc" in resumen["texto"]
    print("check_vulnerabilidades OK")


def main() -> int:
    if "--self-check" in sys.argv:
        auto_check()
        return 0

    errores = []
    total = 0
    fallos = 0
    estado = cargar_estado()
    estado_nuevo = dict(estado)
    try:
        imagenes = seleccionar_imagenes()
        envio_control(f"Iniciando análisis de {len(imagenes)} imágenes", "INFO")
        for imagen in imagenes:
            refs = ", ".join(referencias(imagen) or [imagen["Id"]])
            envio_control(f"Analizando {refs}", "INFO")
            try:
                hallazgos = escanear(imagen)
            except Exception as error:
                fallos += 1
                errores.append(error_fallo(f"No se pudo analizar {refs}: {error}", {"imagen": refs}))
                continue
            total += len(hallazgos)
            if hallazgos:
                nuevas = [hallazgo for hallazgo in hallazgos if clave_hallazgo(hallazgo) not in estado]
                ahora = datetime.now().isoformat(timespec="seconds")
                for hallazgo in hallazgos:
                    estado_nuevo[clave_hallazgo(hallazgo)] = ahora
                if nuevas:
                    errores.append(error_resumen(imagen, hallazgos, len(nuevas)))
                suprimidas = len(hallazgos) - len(nuevas)
                if suprimidas:
                    envio_control(f"{refs}: {suprimidas} vulnerabilidades ya notificadas", "INFO")
            envio_control(f"{refs}: {len(hallazgos)} vulnerabilidades", "WARNING" if hallazgos else "INFO")
    except Exception as error:
        fallos += 1
        errores.append(error_fallo(f"No se pudo iniciar el análisis: {error}"))

    if errores:
        registrar_errores(
            {"email": True, "log": True},
            errores,
            origen=os.getenv("PROYECTO", "docker_vulnerabilidades"),
        )
    if estado_nuevo != estado:
        guardar_estado(estado_nuevo)
    if fallos:
        return 2
    return 1 if total else 0


if __name__ == "__main__":
    raise SystemExit(main())
