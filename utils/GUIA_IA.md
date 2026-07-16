# Guía para IAs — `utils/`

Referencia rápida de las utilidades de esta carpeta. Pensada para que una IA
las use en un proyecto que ya las tenga copiadas en su propio `utils/`.

## Convenciones

- Archivos `.py` autocontenidos en `utils/`. Sin dependencias externas (solo stdlib).
- Cada utilidad expone una clase con estado y/o funciones de un solo uso.
- Configuración por env vars cuando aplica (no se leen argumentos del CLI).
- Cada archivo tiene un self-check ejecutable: `python -m utils.nombre`.
- Cabecera estándar: `# utilidades-python:nombre` + `# __version__ = "X.Y.Z"`.
- Importable siempre como `from utils.nombre import ...`.

## Catálogo

| Módulo | Versión | Símbolo principal | Para qué sirve |
|---|---|---|---|
| `csv_writer` | 1.0.0 | `CSVWriter`, `exportar_csv` | Leer/escribir CSV con cabecera y modo (`sobrescribir`/`anexar`) |
| `text_writer` | 1.0.1 | `TextFileWriter` | Texto plano con append limpio (sin `\n` espurio en archivo nuevo) |
| `json_writer` | 1.0.0 | `JsonFileWriter` | JSON con creación de carpetas padre y `append` dict/list |
| `error_system` | 2.1.0 | `nuevo_error`, `registrar_errores`, `envio_control` | Errores unificados (schema v1) y trazas de control (log stdlib con rotación temporal) |
| `time_utils` | 1.0.0 | `convert_str_en_fecha`, `convert_fecha_en_str`, `es_fecha_valida` | Fechas `YYYYMMDD` (compacto) ↔ `date` y validación |
| `enviar_correo` | 1.0.0 | `EmailWriter` | SMTP con STARTTLS, texto/HTML, context manager, config por env vars |
| `check_updates` | 1.0.0 | (CLI) `python utils/check_updates.py <origen> <destino>` | Detectar actualizaciones entre repos |

## API mínima por utilidad

### `csv_writer`

```python
from utils.csv_writer import CSVWriter, exportar_csv

w = CSVWriter("reporte.csv", ["fecha", "valor", "estado"])
w.write_data(["2026-07-10", "42", "ok"])      # crea/sobrescribe + cabecera + fila
w.add_row(["2026-07-10", "99", "warn"])       # anexa fila
w.read_all()                                  # [{"fecha": "...", ...}]
w.is_empty_csv()                              # bool
w.clear_file()                                # vacía

exportar_csv("reporte.csv", ["v1"], cabecera=["c1"], modo="sobrescribir")  # bool
exportar_csv("reporte.csv", ["v2"], cabecera=["c1"], modo="anexar")        # bool
```

### `text_writer`

```python
from utils.text_writer import TextFileWriter

w = TextFileWriter("/logs/app.log")
w.write_data("inicio")                        # sobrescribe
w.add_line("evento 1")                        # append limpio
w.add_line("evento 2")
w.read_all()                                  # "inicio\nevento 1\nevento 2"
w.clear_file()
```

### `json_writer`

```python
from utils.json_writer import JsonFileWriter

w = JsonFileWriter("/data/estado.json")
w.write({"a": 1, "b": [1, 2, 3]})             # sobrescribe (crea carpetas padre)
w.append({"c": "nuevo"})                      # update si dict, extend si list
w.read()                                      # dict/list o None si no existe
```

### `error_system`

```python
from utils.error_system import (
    nuevo_error,           # fabrica un dict de error (schema v1)
    validar_error,         # bool
    fdatos_keys_errores,   # extrae una clave de cada error
    registrar_errores,     # filtra y escribe JSON (1 fichero por timestamp)
    envio_control,         # log de control (una línea; stdlib logging + rotación temporal)
    SCHEMA_VERSION,        # "1.0"
    TIPOS_VALIDOS,         # ("aviso", "stop", "info")
)

# fabricar
err = nuevo_error(
    tipo="aviso",          # "aviso" | "stop" | "info"
    texto="fallo al escribir CSV",
    notificar_email=True,
    notificar_log=True,
    notificar_bbdd=False,
    contexto={"fichero": "x.csv"},
)

# validar
validar_error(err)         # True

# consultar
tipos = fdatos_keys_errores([err1, err2], "tipo")   # ["aviso", "stop"]

# registrar (filtra por sistema; 1 fichero por llamada)
ruta = registrar_errores(
    sistema={"email": True, "log": True, "bbdd": False},
    errores=[err1, err2],
    origen="mi_proyecto",
    carpeta=None,          # None → env CARPETA_ERRORES o "./notificaciones/"
)                          # → "/.../errores_20260710_120000.json" o None

# trazas (log de control, stdlib logging + TimedRotatingFileHandler)
# config centralizada por env vars: RUTA_CONTROL, LOG_NIVEL, LOG_ROTACION_DIAS,
# LOG_BACKUPS, LOG_FMT, LOG_CONSOLE. Una línea por traza (no toques logger/handlers).
envio_control("inicio del proceso")              # nivel INFO (default)
envio_control("detalle interno", nivel="DEBUG")  # se descarta si LOG_NIVEL=INFO
envio_control("fallo grave", nivel="ERROR")      # se escribe si LOG_NIVEL <= ERROR

# Formato de línea (default LOG_FMT): "2026-07-16 09:30:00,123 | INFO | msg"
# Rotación temporal cada LOG_ROTACION_DIAS (default 15) con LOG_BACKUPS (default 4) ≈ 2 meses
```

#### Migración 1.0.0 → 2.0.0 (`envio_control`)

- Copia `error_system.py` nuevo sobre el viejo y verifica con `python -m utils.error_system` (`v2.0.0 OK`).
- `envio_control("texto")` no cambia — sigue siendo INFO. No toques el código del proyecto.
- `RUTA_CONTROL` ahora apunta a `control.log` (antes `control.txt`); el logger crea uno nuevo. Conserva el histórico renombrando a mano si lo necesitas.
- Las líneas ahora llevan `2026-07-16 09:30:00,123 | INFO | <texto>` — adapta parsers externos con `line.split("|", 2)`.
- Configuración nueva (opcional): `LOG_NIVEL`, `LOG_ROTACION_DIAS`, `LOG_BACKUPS`, `LOG_FMT`, `LOG_CONSOLE`.
- `text_writer.py` ya no lo importa `error_system` (sigue siendo válida por sí sola).
- El schema JSON de errores y el resto de funciones no cambian.

#### Migración 2.0.0 → 2.1.0 (defaults de rutas)

- Solo cambian los defaults de `RUTA_CONTROL` (`./control.log` → `./logs/control.log`) y `CARPETA_ERRORES` (`./errores/` → `./notificaciones/`). Los nombres de las env vars no cambian.
- Los ficheros rotated por `TimedRotatingFileHandler` viven junto al activo (en `./logs/`).
- Si ya tenías `.env` con `RUTA_CONTROL` o `CARPETA_ERRORES` seteados, no te afecta: tus valores siguen ganando. Si los dejabas sin setear, los JSON y logs ahora caerán en `./notificaciones/` y `./logs/` respectivamente (carpetas se autosecrean).

### `time_utils`

```python
from datetime import date
from utils.time_utils import (
    convert_str_en_fecha,  # "YYYYMMDD" → date, lanza ValueError si no válido
    convert_fecha_en_str,  # date → "YYYYMMDD"
    es_fecha_valida,       # date o "YYYY-MM-DD" → bool
)

d = convert_str_en_fecha("20260710")     # date(2026, 7, 10)
s = convert_fecha_en_str(date.today())   # "20260710"
es_fecha_valida("2026-07-10")            # True
es_fecha_valida("20260710")              # False (compacto no soportado aquí)
```

### `enviar_correo`

```python
from utils.enviar_correo import EmailWriter

# Lee de env: EMISOR_CORREO, PASS_CORREO, RECEPTOR_CORREO (csv),
#            ASUNTO (default "UPS ALERTA"), TEXTO (default ""),
#            SMTP_HOST (default "smtp.gmail.com"), SMTP_PORT (default 587)

with EmailWriter() as m:                # context manager: cierra al salir
    m.conectar()                        # SMTP + EHLO + STARTTLS + login
    m.enviar("asunto", "cuerpo")        # texto plano
    m.enviar("html", "<h1>x</h1>", html=True)
```

Sin context manager:

```python
m = EmailWriter()
m.conectar()
m.enviar()                              # usa ASUNTO y TEXTO de env
m.cerrar()
```

Levanta `ValueError` si `conectar()` se llama sin `EMISOR_CORREO`/`PASS_CORREO`/`RECEPTOR_CORREO`. Levanta `RuntimeError` si `enviar()` se llama antes de `conectar()`.

### `check_updates` (CLI, no importable)

```bash
python utils/check_updates.py <directorio_utils_origen> <directorio_utils_destino>
```

Salida: tabla con estados `OK` / `DESACTUALIZADO` / `FALTA_EN_DESTINO` / `MAS_NUEVO_EN_DESTINO` / `SIN_VERSION`. Exit codes: `0` todo OK, `1` hay problemas, `2` error de args. Sin args corre self-check.

## Env vars

| Variable | Usada por | Default | Notas |
|---|---|---|---|
| `CARPETA_ERRORES` | `error_system` | `./notificaciones/` | Carpeta destino de los JSON de errores |
| `RUTA_CONTROL` | `error_system` (log) | `./logs/control.log` | Fichero de log de control (TimedRotatingFileHandler). Los ficheros rotated viven en el mismo dir |
| `LOG_NIVEL` | `error_system` (log) | `INFO` | `DEBUG\|INFO\|WARNING\|ERROR\|CRITICAL` — filtra lo que se emite |
| `LOG_ROTACION_DIAS` | `error_system` (log) | `15` | Días entre rotaciones |
| `LOG_BACKUPS` | `error_system` (log) | `4` | Nº de ficheros rotated conservados (15×4 ≈ 2 meses) |
| `LOG_FMT` | `error_system` (log) | `%(asctime)s \| %(levelname)s \| %(message)s` | Formato de línea (logging.Formatter) |
| `LOG_CONSOLE` | `error_system` (log) | `0` | `1` → emitir también a stderr |
| `EMISOR_CORREO` | `enviar_correo` | — | Remitente (obligatorio) |
| `PASS_CORREO` | `enviar_correo` | — | App password de Gmail (obligatorio) |
| `RECEPTOR_CORREO` | `enviar_correo` | — | CSV de destinatarios (obligatorio) |
| `ASUNTO` | `enviar_correo` | `UPS ALERTA` | Subject por defecto |
| `TEXTO` | `enviar_correo` | `""` | Cuerpo por defecto |
| `SMTP_HOST` | `enviar_correo` | `smtp.gmail.com` | Servidor SMTP |
| `SMTP_PORT` | `enviar_correo` | `587` | Puerto STARTTLS |

## Patrones de uso frecuentes

### 1. Scraping → CSV + log + errores

```python
from datetime import date
from utils.csv_writer import exportar_csv
from utils.error_system import (
    nuevo_error, registrar_errores, envio_control, fdatos_keys_errores,
)

SISTEMA = {"email": True, "log": True, "bbdd": False}
errores = []
envio_control(f"=== Inicio {date.today()} ===")

try:
    archivo = f"/data/scraper_{date.today().isoformat()}.csv"
    exportar_csv(archivo, ["42", "ok"], ["valor", "estado"], "sobrescribir")
    envio_control("CSV escrito")
except Exception as e:
    errores.append(nuevo_error(
        tipo="aviso", texto=f"fallo X: {e}",
        notificar_email=True, notificar_log=True,
        contexto={"fase": "main"},
    ))

if errores:
    tipos = fdatos_keys_errores(errores, "tipo")
    envio_control(f"Registrando {len(errores)} errores, tipos={tipos}")
    registrar_errores(SISTEMA, errores, origen="scraper_v1")
```

### 2. Daemon que consume los JSON de errores y los envía por email

```python
import glob, os, time
from utils.enviar_correo import EmailWriter
from utils.json_writer import JsonFileWriter
from utils.error_system import SCHEMA_VERSION, validar_error

def procesar(ruta: str, m: EmailWriter) -> None:
    payload = JsonFileWriter(ruta).read()
    if not payload or payload.get("schema_version") != SCHEMA_VERSION:
        return
    for err in payload.get("errores", []):
        if not validar_error(err):
            continue
        if not err.get("notificacion", {}).get("email"):
            continue
        m.enviar(
            asunto=f"[{payload.get('origen')}] {err['tipo']}: {err['texto'][:50]}",
            cuerpo=f"{err['texto']}\n\nContexto: {err.get('contexto')}",
        )
    os.remove(ruta)

def main():
    with EmailWriter() as m:
        m.conectar()
        while True:
            for ruta in glob.glob("./errores/errores_*.json"):
                try:
                    procesar(ruta, m)
                except Exception as e:
                    print(f"fallo procesando {ruta}: {e}")
            time.sleep(60)
```

### 3. Estado persistente entre ejecuciones

```python
from utils.json_writer import JsonFileWriter

ESTADO = "/data/estado.json"
w = JsonFileWriter(ESTADO)
estado = w.read() or {}
ultima = estado.get("ultima_jornada", 0)
# ... procesar ...
w.append({"ultima_jornada": ultima + 1})
```

## Reglas de oro

- **Copia archivo a archivo**, no instales como paquete. Cada `.py` es una unidad.
- **No mezcles responsabilidades.** `error_system` produce JSON; `enviar_correo` los envía; el daemon que los une es código del proyecto, no de la librería.
- **Usa `contexto` en los errores.** Es el punto de extensión — añade ahí datos específicos del proyecto (jornada, temporada, etc.).
- **Self-check = test mínimo.** Si tocas una utilidad, corre `python -m utils.X` antes de cerrar el cambio.
- **No quites la cabecera `# __version__`.** `check_updates` la lee.

## Schema JSON v1 de errores (producido por `registrar_errores`)

```json
{
  "schema_version": "1.0",
  "timestamp_creacion": "2026-07-10T09:30:00",
  "origen": "nombre_proyecto_o_proceso",
  "errores": [
    {
      "tipo": "aviso | stop | info",
      "texto": "descripción legible",
      "timestamp": "2026-07-10T09:25:00",
      "dia": "2026-07-10",
      "notificacion": {"email": true, "log": true, "bbdd": false},
      "contexto": {"cualquier_campo_extra": "..."}
    }
  ]
}
```

Esta guía es autocontenida: asume que solo tienes acceso a esta carpeta (`utils/`) y a los `.py` que lista el catálogo. Si necesitas información que no esté aquí, busca dentro de los propios archivos `.py` (cabecera con `# __version__` y docstring de API al inicio de cada uno).
