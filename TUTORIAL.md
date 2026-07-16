# Tutorial de uso por utilidad

Guía detallada, una sección por archivo `.py`, con ejemplos prácticos para casos reales. Si solo quieres el overview + cómo empezar, mira `README.md`. Este documento es la referencia profunda.

Índice:

- [Diccionario de variables de entorno](#diccionario-de-variables-de-entorno)
- [Instalación, actualización y verificación](#instalación-actualización-y-verificación)
- [csv_writer.py](#csv_writerpy)
- [text_writer.py](#text_writerpy)
- [json_writer.py](#json_writerpy)
- [error_system.py](#error_systempy)
- [time_utils.py](#time_utilspy)
- [enviar_correo.py](#enviar_correopy)
- [enviar_notificaciones.py](#enviar_notificacionespy)
- [check_updates.py](#check_updatespy)

---

## Diccionario de variables de entorno

Solo `error_system`, `enviar_correo` y `enviar_notificaciones` usan env vars.
El resto (`csv_writer`, `text_writer`, `json_writer`, `time_utils`,
`check_updates`) son stdlib puro sin configuración por entorno. Cada bloque es
**copia-pega a `.env`**; los valores mostrados son los defaults (sustituye por
los tuyos).

### `error_system`

```bash
# Carpeta destino de los JSON de notificaciones (uno por cada registrar_errores)
CARPETA_ERRORES=./notificaciones/
# Nombre del proyecto; default del campo `origen` si no pasas origen a registrar_errores
PROYECTO=mi_proyecto
# Fichero de log activo; los rotated (TimedRotatingFileHandler) viven junto a este
RUTA_CONTROL=./logs/control.log
# Nivel mínimo: DEBUG | INFO | WARNING | ERROR | CRITICAL
LOG_NIVEL=INFO
# Días entre rotaciones · Nº de backups retenidos (retención ≈ días × backups)
LOG_ROTACION_DIAS=15
LOG_BACKUPS=4
# Formato de línea (sintaxis logging.Formatter)
LOG_FMT=%(asctime)s | %(levelname)s | %(message)s
# 1 → emitir también a stderr · 0 → solo fichero
LOG_CONSOLE=0
```

### `enviar_correo`

```bash
# Remitente (cuenta Gmail completa) · Obligatorio
EMISOR_CORREO=tu_correo@gmail.com
# App password de Google (16 chars, NO la password normal). Genera una en myaccount.google.com/apppasswords · Obligatorio
PASS_CORREO=tu_app_password
# Destinatarios separados por coma · Obligatorio (para uso directo de EmailWriter)
RECEPTOR_CORREO=dest1@x.com,dest2@x.com
# Asunto y cuerpo por defecto (sobreescribibles en cada enviar())
ASUNTO=UPS ALERTA
TEXTO=
# SMTP host:port · 587=STARTTLS · 465=SMTPS implícito
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
```

### `enviar_notificaciones`

```bash
# Reutiliza SMTP: EMISOR_CORREO, PASS_CORREO, SMTP_HOST, SMTP_PORT de enviar_correo
# Faltan creds → el daemon se queja y no procesa (verLogs en control.log).
# EMAIL_GENERICO: To por defecto si un error no trae to_email · Obligatorio en prácticas
EMAIL_GENERICO=alertas@midominio.com
# Carpeta pendientes (mismo default que error_system). Lee los errores_*.json de aquí
CARPETA_ERRORES=./notificaciones/
# Subcarpeta destino tras procesar cada JSON (se crea sola)
ENVIADOS_DIR=./notificaciones/enviados/
# Horas mínimas en ENVIADOS_DIR antes de borrarse en la siguiente pasada
RETENCION_HORAS=24
# Log de control heredado de error_system (RUTA_CONTROL, LOG_NIVEL, ...)
```

---

## Instalación, actualización y verificación

### Instalar una utilidad en tu proyecto

Este repo **no es un paquete pip**: se copia archivo a archivo. Para cada
utilidad que necesites, copia su `.py` a la carpeta `utils/` de tu proyecto:

```bash
# desde la raíz de tu proyecto (o donde quieras)
mkdir -p mi_proyecto/utils
cp /workspace/utilidades_python/utils/<utilidad>.py mi_proyecto/utils/
```

Ejemplos:

```bash
cp /workspace/utilidades_python/utils/csv_writer.py     mi_proyecto/utils/
cp /workspace/utilidades_python/utils/error_system.py   mi_proyecto/utils/
cp /workspace/utilidades_python/utils/json_writer.py    mi_proyecto/utils/
```

Importa siempre como `from utils.<utilidad> import ...`.

### Dependencias entre utilidades

La mayoría son autocontenidas (solo stdlib). Solo una tiene dependencia
interna:

| Utilidad | Depende de | Notas |
|---|---|---|
| `error_system` | `json_writer` | Para escribir los JSON de errores. El log de control (`envio_control`) usa stdlib `logging`, no `text_writer`. |
| `enviar_notificaciones` | `enviar_correo`, `json_writer`, `error_system` | Lee JSONs, despacha por SMTP y traza en el log de control. |
| `csv_writer`, `text_writer`, `json_writer`, `time_utils`, `enviar_correo`, `check_updates` | — | Autocontenidas |

Copia siempre las dependencias junto con la utilidad (en este caso,
`error_system` y `json_writer` van juntos).

### Verificar que funciona (self-check)

Cada utilidad trae un self-check ejecutable. Sin argumentos, corre pruebas
internas y muestra `vX.Y.Z OK` al final:

```bash
python -m utils.csv_writer
python -m utils.error_system
# ... con cualquier utilidad
```

Útil tras copiar un archivo o tras modificarlo: si ves `OK`, está sano.

### Comprobar si tus copias están actualizadas

`check_updates.py` compara las versiones de este repo (origen) con las de tu
proyecto (destino):

```bash
python utils/check_updates.py /workspace/utilidades_python/utils/  ~/work/mi_proyecto/utils/
```

Reporta estados `OK` / `DESACTUALIZADO` / `FALTA_EN_DESTINO` /
`MAS_NUEVO_EN_DESTINO` / `SIN_VERSION` (ver [interpretación de
estados](#interpretación-de-estados)). Exit codes: `0` todo OK, `1` hay
problemas, `2` error de argumentos/rutas. Para ejemplos, bucle para varios
proyectos y errores comunes, ver [check_updates.py](#check_updatespy).

### Actualizar una utilidad

Cuando `check_updates` marque `DESACTUALIZADO` o `FALTA_EN_DESTINO`, recopia
el archivo desde el origen y vuelve a correr el self-check:

```bash
cp /workspace/utilidades_python/utils/error_system.py mi_proyecto/utils/
python -m utils.error_system   # debe decir v2.0.0 OK
```

Si el cambio es major (p.ej. `error_system` 1.0.0 → 2.0.0), revisa la nota de
migración en la sección de esa utilidad (puede haber breaking changes, como
el cambio de `control.txt` a `control.log`).

---

## csv_writer.py

### Cuándo copiarlo a tu proyecto

- Generas reportes en CSV (scrapers, exports de BBDD, listados)
- Necesitas anexar filas a un CSV existente sin romper la cabecera
- Quieres leer un CSV como lista de dicts

### API mínima (cubre el 80% de los casos)

```python
from utils.csv_writer import exportar_csv

# Escribir/reemplazar un CSV con cabecera y una fila
exportar_csv(
    filename="reporte.csv",
    datos=["2026-07-10", "42", "ok"],
    cabecera=["fecha", "valor", "estado"],
    modo="sobrescribir",
)
```

```python
# Anexar una fila al CSV existente
exportar_csv(
    filename="reporte.csv",
    datos=["2026-07-10", "99", "warn"],
    cabecera=["fecha", "valor", "estado"],
    modo="anexar",
)
```

`exportar_csv` decide internamente:

- Si el archivo no existe o `modo="sobrescribir"` → escribe cabecera + fila
- Si el archivo existe, `modo="anexar"` y NO está vacío → añade fila al final
- Si el archivo existe, `modo="anexar"` pero está vacío → escribe cabecera + fila

### API completa (clase `CSVWriter`)

```python
from utils.csv_writer import CSVWriter

w = CSVWriter("reporte.csv", ["fecha", "valor", "estado"])

w.write_data(["2026-07-10", "42", "ok"])   # sobrescribe + cabecera
w.add_row(["2026-07-10", "99", "warn"])    # anexa fila
w.is_empty_csv()                            # bool
w.clear_file()                              # vacía
w.read_all()                                # [{"fecha": "...", "valor": "42", ...}, ...]
```

### Ejemplo real: scraper que escribe un CSV diario

```python
# en mi_scraper/main.py
from datetime import date
from utils.csv_writer importar exportar_csv

def escribir_reporte(datos_hoy: list[str]):
    nombre = f"/data/reportes/reporte_{date.today().isoformat()}.csv"
    exportar_csv(
        filename=nombre,
        datos=datos_hoy,
        cabecera=["equipo", "goles", "resultado"],
        modo="sobrescribir",   # siempre empezamos de cero
    )

def volcar_evento_a_log(equipo: str, goles: int):
    nombre = "/data/logs/eventos.csv"
    exportar_csv(
        filename=nombre,
        datos=[str(date.today()), equipo, str(goles)],
        cabecera=["fecha", "equipo", "goles"],
        modo="anexar",         # sumamos al log
    )
```

### Ejemplo real: leer un CSV y procesarlo

```python
from utils.csv_writer import CSVWriter

# leer como lista de dicts
filas = CSVWriter("/data/reporte.csv", []).read_all()
for fila in filas:
    print(fila["equipo"], fila["goles"])
```

`CSVWriter` requiere `headers` para instanciarse, pero para `read_all()` los headers salen del propio archivo, así que puedes pasar `[]` si solo vas a leer.

### Errores comunes

- **Pasar `modo` en mayúsculas o con typo** → `"Sobrescribir"` no es `"sobrescribir"`. La comparación es literal.
- **Olvidar `cabecera` en `anexar`** → la primera vez que anexas sin cabecera, las columnas quedan sin nombre. Ponla siempre, también al anexar.
- **Usar `write_data` pensando que anexa** → `write_data` con `mode='w'` (default) SIEMPRE sobrescribe. Para anexar usa `add_row` o `write_data(mode='a')`.
- **Leer CSV sin `read_all` y esperar lista de listas** → `read_all` devuelve lista de dicts. Si quieres listas, lee el CSV con `csv.reader` a pelo.

---

## text_writer.py

### Cuándo copiarlo

- Necesitas un log plano de ejecución (`.txt` o `.log`)
- Quieres un sistema de trazas simple (inicio, fin, eventos) sin overhead de logging de Python
- Cualquier escritura/append de fichero de texto

### API mínima

```python
from utils.text_writer import TextFileWriter

w = TextFileWriter("/logs/mi_app.log")
w.write_data("inicio del proceso")   # sobrescribe
w.add_line("evento 1")               # append limpio
w.add_line("evento 2")
```

Tras esos 3 llamadas, el archivo contiene:
```
inicio del proceso
evento 1
evento 2
```

### API completa

```python
w = TextFileWriter("/logs/mi_app.log")
w.write_data("texto", mode="w")      # default; sobrescribe
w.write_data("texto", mode="a")      # anexa con \n si archivo no vacío
w.add_line("texto")                  # atajo de write_data(texto, 'a')
w.read_all()                         # "inicio\nevento 1\nevento 2" o "" si no existe
w.clear_file()                       # vacía
w._file_exists()                     # bool, método "privado" pero público de facto
```

### Ejemplo real: log diario de un cron

```python
# cron diario que ejecuta esto
from datetime import date
from utils.text_writer import TextFileWriter

def log(mensaje: str):
    w = TextFileWriter(f"/logs/cron_{date.today().isoformat()}.log")
    w.add_line(f"[{date.today()}] {mensaje}")

log("inicio")
log("procesando batch 1")
log("batch 1 OK")
log("procesando batch 2")
log("batch 2 falló")
log("fin")
```

Resultado en `/logs/cron_2026-07-10.log`:
```
[2026-07-10] inicio
[2026-07-10] procesando batch 1
[2026-07-10] batch 1 OK
[2026-07-10] procesando batch 2
[2026-07-10] batch 2 falló
[2026-07-10] fin
```

### Errores comunes

- **Asumir que `add_line` añade línea vacía entre llamadas** → añade `\n` solo si el archivo no está vacío. La primera línea no tiene `\n` precedente. Esto es lo correcto para que el archivo sea legible, pero si esperas lo contrario, usa `write_data` con `'\n' + texto` manual.
- **Usar para logs estructurados** → `text_writer` es para texto plano. Si necesitas niveles, timestamps automáticos, rotación o filtrado, usa `logging` de stdlib o una lib.
- **Múltiples procesos escribiendo al mismo fichero** → no hay lock. Para escrituras concurrentes usa un lock (`fcntl.flock` o similar) por tu cuenta.

---

## json_writer.py

### Cuándo copiarlo

- Persistir estado simple entre ejecuciones (última fecha procesada, contador, etc.)
- Cachear respuestas de APIs externas
- Generar ficheros de configuración editables a mano
- Cualquier JSON que se lea y modifique repetidamente

### API mínima

```python
from utils.json_writer import JsonFileWriter

w = JsonFileWriter("/data/estado.json")
w.write({"ultima_ejecucion": "2026-07-10", "status": "ok"})
# más tarde...
w.append({"contador": 42})           # mezcla con lo existente (dict)
```

Si el fichero no existe, `append` lo crea. Si existe, carga el dict, hace `update()` con lo nuevo, y reescribe.

### API completa

```python
w = JsonFileWriter("/data/x.json")

w.write({"a": 1})                    # sobrescribe (crea carpetas padre)
w.append({"b": 2})                   # update si dict, extend si list
w.read()                             # {"a": 1, "b": 2} o None si no existe / vacío
```

### Ejemplo real: estado de un scraper

```python
# mi_scraper/estado.py
from utils.json_writer import JsonFileWriter

ESTADO_PATH = "/data/scraper/estado.json"

def obtener_estado() -> dict:
    return JsonFileWriter(ESTADO_PATH).read() or {}

def actualizar_estado(cambios: dict) -> None:
    JsonFileWriter(ESTADO_PATH).append(cambios)

# uso
estado = obtener_estado()
ultima = estado.get("ultima_jornada", 0)
# ... procesar ...
actualizar_estado({"ultima_jornada": ultima + 1, "ultimo_timestamp": "2026-07-10T12:00:00"})
```

### Ejemplo real: cache de respuestas externas

```python
import time
from utils.json_writer import JsonFileWriter

CACHE = "/data/cache/api_externa.json"

def llamada_con_cache(params: dict, ttl_segundos: int = 3600):
    cache = JsonFileWriter(CACHE)
    estado = cache.read() or {"timestamp": 0, "data": None}
    if time.time() - estado["timestamp"] < ttl_segundos:
        return estado["data"]
    # ... llamada real a la API ...
    respuesta = {"valor": 42}
    cache.write({"timestamp": time.time(), "data": respuesta})
    return respuesta
```

### Ejemplo real: lista acumulativa (eventos)

```python
from utils.json_writer import JsonFileWriter

w = JsonFileWriter("/data/eventos.json")
w.write([])                                 # inicializa como lista vacía
w.append([{"ts": "2026-07-10", "evt": "x"}])
w.append([{"ts": "2026-07-10", "evt": "y"}])
# w.read() → [{"ts": "2026-07-10", "evt": "x"}, {"ts": "2026-07-10", "evt": "y"}]
```

### Errores comunes

- **`append` con tipos incompatibles** → si el JSON existente es dict, no puedes hacer `append(["lista"])`. Lanza `TypeError`. Decide de antemano: ¿el fichero es dict o lista?
- **Confundir `write` con sobrescritura parcial** → `write` reemplaza TODO. Para mezcla, usa `append`.
- **No validar el JSON antes de leer** → `read()` puede devolver `None` (archivo inexistente) o lo que sea que haya dentro. Si tu código asume estructura, valida con `isinstance(resultado, dict)`.

---

## error_system.py

### Cuándo copiarlo

- Cualquier proyecto que necesite registrar errores sin enviarlos directamente (los envia un daemon después)
- Proyectos con múltiples canales de notificación (email, log, BBDD) y quieres una fuente única
- Necesitas trazabilidad: agrupar errores por día, contar tipos, etc.

> **Dependencia:** requiere `json_writer.py` (lo importa). Recuerda copiar
> ambos. El log de control (`envio_control`) usa stdlib `logging`. Ver
> [Dependencias entre utilidades](#dependencias-entre-utilidades).

### Configuración (.env)

```bash
# Errores → JSON (un fichero por llamada a registrar_errores)
CARPETA_ERRORES=/var/log/mi_proyecto/notificaciones

# Nombre del proyecto; default del campo `origen` del JSON si no pasas origen a registrar_errores
PROYECTO=mi_proyecto

# Log de control (envio_control) — stdlib logging + TimedRotatingFileHandler
RUTA_CONTROL=/var/log/mi_proyecto/logs/control.log
LOG_NIVEL=INFO                 # DEBUG | INFO | WARNING | ERROR | CRITICAL
LOG_ROTACION_DIAS=15          # rota el log cada 15 días
LOG_BACKUPS=4                 # conserva 4 ficheros (~60 días ≈ 2 meses)
LOG_FMT=%(asctime)s | %(levelname)s | %(message)s
LOG_CONSOLE=0                 # 1 → también emite a stderr
```

> **Defaults sin .env (2.1.0+):** si no seteas nada, los JSON caen en
> `./notificaciones/` y el log de control (activo + backups rotated) en
> `./logs/control.log`. Las carpetas se crean solas. Setea las env vars solo
> si quieres otra ubicación.

### API mínima

```python
from utils.error_system import nuevo_error, registrar_errores, envio_control

SISTEMA = {"email": True, "log": True, "bbdd": False}
errores = []

try:
    # ... tu código que puede fallar ...
    envio_control("procesando X")
except Exception as e:
    errores.append(nuevo_error(
        tipo="aviso",
        texto=f"Falló X: {e}",
        notificar_email=True,
        notificar_log=True,
        contexto={"fase": "X"},
    ))

if errores:
    registrar_errores(SISTEMA, errores, origen="mi_proyecto")
```

### API completa

```python
from utils.error_system import (
    nuevo_error,        # fábrica de dicts (schema v1.1 desde 2.2.0)
    validar_error,      # valida contra schema v1 (no exige campos v1.1 opcionales)
    fdatos_keys_errores, # extrae una clave de cada error
    registrar_errores,  # filtra y escribe JSON
    envio_control,      # trazas a fichero de control
    SCHEMA_VERSION,     # "1.0"
    TIPOS_VALIDOS,      # ("aviso", "stop", "info")
)

# fabricar (sin v1.1: como siempre)
err = nuevo_error(
    tipo="stop",                      # "aviso" | "stop" | "info"
    texto="jornada incompleta",
    notificar_email=True,
    notificar_log=True,
    notificar_bbdd=False,
    contexto={"jornada": 12, "temporada": 2026},
)

# fabricar con destinatarios por error (v1.1, opcional). Si no pasas from_email/to_email
# el dict del error NO lleva esas claves (backward compatible con JSONs legacy).
err_dest = nuevo_error(
    tipo="stop",
    texto="no hay stock",
    notificar_email=True,
    contexto={"producto": "SKU-9"},
    from_email="shop@midominio.com",  # opcional: From de este correo concreto
    to_email="ops@midominio.com,oncall@midominio.com",  # opcional: To concreto (CSV)
)
# Sin estos campos, enviar_notificaciones cae a EMAIL_GENERICO (ver su sección).

# validar (lanza excepción si quieres fallar fuerte)
if not validar_error(err):
    raise ValueError(f"error mal formado: {err}")

# consultar
tipos = fdatos_keys_errores(errores, "tipo")    # ["aviso", "stop", ...]
dias  = fdatos_keys_errores(errores, "dia")     # ["2026-07-10", ...]

# registrar (1 fichero por llamada con timestamp)
ruta = registrar_errores(
    sistema={"email": True, "log": True, "bbdd": False},
    errores=errores,
    origen="mi_proyecto",          # aparece en el JSON. Si pasas None o lo omites,
                                   # cae a env PROYECTO y, si no está, a "desconocido".
    carpeta=None,                  # None = usa env CARPETA_ERRORES o "./notificaciones/"
)
# ruta → "/var/log/.../notificaciones/errores_20260710_120000_123456.json" o None si no había nada

# trazas de control (log de ejecución, stdlib logging + rotación temporal)
# config centralizada por env vars (RUTA_CONTROL, LOG_NIVEL, ...). Una línea por traza.
envio_control("inicio")                       # nivel INFO (default)
envio_control("detalle", nivel="DEBUG")        # se descarta si LOG_NIVEL=INFO
envio_control("fallo", nivel="ERROR")         # se escribe si LOG_NIVEL <= ERROR
envio_control("fin")
# formato de línea (default LOG_FMT):
#   2026-07-16 09:30:00,123 | INFO | inicio
# rotación automática cada LOG_ROTACION_DIAS (default 15), reteniendo LOG_BACKUPS (default 4) ≈ 2 meses
```

### Ejemplo real: scraper con notificación

```python
# mi_scraper/main.py
import time
from datetime import date
from dotenv import load_dotenv

from utils.error_system import (
    nuevo_error, registrar_errores, envio_control, fdatos_keys_errores
)

load_dotenv()

SISTEMA = {"email": True, "log": True, "bbdd": False}
errores = []

envio_control(f"=== Inicio scraper {date.today()} ===")
inicio = time.time()

try:
    # ... descargar ...
    envio_control("descarga OK")
    # ... procesar ...
    envio_control("proceso OK")
except Exception as e:
    errores.append(nuevo_error(
        tipo="stop",                          # el proceso no puede continuar
        texto=f"Error general: {e}",
        notificar_email=True,
        notificar_log=True,
        contexto={"fase": "main", "timestamp": str(date.today())},
    ))

# antes de cada fase importante, registra errores parciales
try:
    resultado = procesar_jornada(jornada)
except ValueError as e:
    errores.append(nuevo_error(
        tipo="aviso",                         # no para el proceso
        texto=f"Datos mal formateados: {e}",
        notificar_email=True,
        notificar_log=True,
        contexto={"fase": "procesar", "jornada": jornada},
    ))

# al final
envio_control(f"Duración: {time.time()-inicio:.2f}s")
if errores:
    tipos = fdatos_keys_errores(errores, "tipo")
    envio_control(f"Registrando {len(errores)} errores, tipos={tipos}")
    ruta = registrar_errores(SISTEMA, errores, origen="scraper_v1")
    envio_control(f"Errores en: {ruta}")
envio_control("=== Fin ===")
```

### Ejemplo real: pipeline con control de parada por "stop"

```python
# pipeline que para si ve un error de tipo "stop"
errores = []
for paso in ["descargar", "validar", "cargar"]:
    try:
        ejecutar(paso)
    except Exception as e:
        errores.append(nuevo_error(
            tipo="stop",                      # para el pipeline
            texto=f"paso {paso} falló: {e}",
            notificar_email=True,
        ))
        break

# si hay algún "stop", no continuar
if "stop" in fdatos_keys_errores(errores, "tipo"):
    print("Pipeline abortado por error crítico")
    registrar_errores(SISTEMA, errores, origen="pipeline")
    exit(1)
```

### Errores comunes

- **Olvidar filtrar por sistema** → `registrar_errores` ya filtra errores cuyo `notificacion` no tiene ningún canal activo. Pero si todos los flags de `sistema` son False, devuelve `None` (no escribe nada). Tenlo en cuenta.
- **Hardcodear la carpeta de errores** → usa la env var `CARPETA_ERRORES`. Si no, mover de máquina es un dolor.
- **Confundir `tipo="aviso"` con `tipo="info"`** → `aviso` = algo va mal pero el proceso sigue. `stop` = no se puede continuar. `info` = anotación que quieres que se notifique igual. Los tres producen JSON, pero el daemon puede tratarlos distinto.
- **No usar `contexto`** → el campo `contexto` está ahí para que el daemon no tenga que adivinar. Si tu error es "fallo en jornada 12", pon `contexto={"jornada": 12}`.
- **Llamar `registrar_errores` con la lista vacía** → devuelve `None` sin escribir nada. Útil para no generar ficheros inútiles, pero no confundas con error.
- **Parser antiguo de `control.txt`** (migración 2.0.0) → las líneas ahora llevan timestamp y nivel (`2026-07-16 09:30:00,123 | INFO | msg`). Adapta los parsers que leían el texto plano. La llamada `envio_control("texto")` sigue funcionando sin cambios.
- **Cambiar `LOG_NIVEL` en caliente** → `envio_control` reaplica el nivel en cada llamada, pero los handlers se crean una sola vez (ruta, formato y rotación se fijan en la primera traza). Para cambiar esos, reinicia el proceso.
- **`LOG_BACKUPS` insuficiente para retención larga** → 15 días × 4 ≈ 2 meses. Sube `LOG_BACKUPS` o `LOG_ROTACION_DIAS` si necesitas más histórico.

---

## time_utils.py

### Cuándo copiarlo

- Tu sistema usa formato compacto `YYYYMMDD` para nombres de archivo o claves (común en legacy, SAP, ciertos APIs)
- Necesitas conversión bidireccional `date` ↔ string
- Validas fechas de input que pueden venir en distintos formatos

### Instalación

```bash
cp /workspace/utilidades_python/utils/time_utils.py mi_proyecto/utils/
```

### API

```python
from datetime import date
from utils.time_utils import convert_str_en_fecha, convert_fecha_en_str, es_fecha_valida

# string compacto "YYYYMMDD" → date
d = convert_str_en_fecha("20260710")         # date(2026, 7, 10)
d = convert_str_en_fecha("20000101")         # date(2000, 1, 1)
# lanza ValueError si no son 8 chars o los componentes no son válidos

# date → string compacto "YYYYMMDD"
s = convert_fecha_en_str(date(2026, 7, 10))  # "20260710"
s = convert_fecha_en_str(date.today())       # "20260710" (si hoy es 2026-07-10)

# validar
es_fecha_valida(date(2026, 7, 10))           # True
es_fecha_valida("2026-07-10")                # True (formato extendido)
es_fecha_valida("2026-13-40")                # False
es_fecha_valida("20260710")                  # False (formato compacto no soportado aquí)
es_fecha_valida(None)                        # False
es_fecha_valida(12345)                       # False
```

**Importante**: hay DOS formatos en juego:

- `convert_*` → compacto `YYYYMMDD` (8 chars, sin separadores)
- `es_fecha_valida` → acepta `date` o extendido `YYYY-MM-DD` (10 chars, con guiones)

Si necesitas validar un string compacto, pásalo por `convert_str_en_fecha` y captura la excepción:

```python
try:
    d = convert_str_en_fecha(input_usuario)
    # válido
except ValueError:
    # inválido
```

### Ejemplo real: nombre de archivo diario

```python
from datetime import date
from utils.time_utils import convert_fecha_en_str

def ruta_reporte_hoy() -> str:
    return f"/data/reportes/reporte_{convert_fecha_en_str(date.today())}.csv"

# /data/reportes/reporte_20260710.csv
```

### Ejemplo real: parsear fecha de un input externo

```python
from utils.time_utils import convert_str_en_fecha, es_fecha_valida
from datetime import date

def parsear_fecha(texto: str) -> date:
    """Acepta 'YYYYMMDD' o 'YYYY-MM-DD' y devuelve date."""
    if not texto:
        raise ValueError("fecha vacía")

    # ¿es compacto?
    try:
        return convert_str_en_fecha(texto)
    except ValueError:
        pass

    # ¿es extendido?
    if es_fecha_valida(texto):
        y, m, d = texto.split("-")
        return date(int(y), int(m), int(d))

    raise ValueError(f"formato no reconocido: {texto!r}")
```

### Ejemplo real: validar input de usuario

```python
from utils.time_utils import es_fecha_valida

def pedir_fecha_al_usuario() -> str:
    while True:
        texto = input("Introduce fecha (YYYY-MM-DD): ").strip()
        if es_fecha_valida(texto):
            return texto
        print("Formato inválido, intenta de nuevo")
```

### Errores comunes

- **Asumir que `es_fecha_valida` acepta `YYYYMMDD`** → no lo hace, solo `date` o `YYYY-MM-DD`. Para compacto usa `convert_str_en_fecha` y captura.
- **Capturar cualquier excepción** → `convert_str_en_fecha` lanza `ValueError`, no `Exception`. Sé específico.
- **Construir fechas con `datetime.strptime` cuando ya tienes `date`** → si ya tienes `date`, úsalo. `es_fecha_valida` lo detecta automáticamente.

---

## enviar_correo.py

### Cuándo copiarlo

- Tu proyecto necesita enviar correo desde un script o un daemon (alertas, reportes, notificaciones)
- Ya produces errores vía `error_system.py` y quieres un script aparte que los lea del JSON y los mande por email
- Quieres reemplazar el envío manual de `docker run ... correo-docker` por una llamada Python

### Instalación

```bash
cp /workspace/utilidades_python/utils/enviar_correo.py mi_proyecto/utils/
```

No tiene dependencias externas. Solo stdlib (`smtplib`, `email`).

### Configuración (.env)

```bash
EMISOR_CORREO=tu_correo@gmail.com
PASS_CORREO=tu_app_password           # NO la password normal, la "app password" de Google
RECEPTOR_CORREO=dest1@x.com,dest2@x.com   # separados por coma
ASUNTO=UPS ALERTA
TEXTO=                               # opcional, también se puede pasar en enviar()
SMTP_HOST=smtp.gmail.com             # default
SMTP_PORT=587                        # default (STARTTLS)
```

`ASUNTO`, `TEXTO`, `SMTP_HOST` y `SMTP_PORT` son opcionales. `EMISOR_CORREO`, `PASS_CORREO` y `RECEPTOR_CORREO` son obligatorios para `conectar()`.

### API mínima (con context manager)

```python
from utils.enviar_correo import EmailWriter

with EmailWriter() as m:
    m.conectar()
    m.enviar("hola", "cuerpo del mensaje")           # texto plano
    m.enviar("alerta", "<h1>algo falló</h1>", html=True)
# al salir del with se cierra la conexión SMTP
```

### API completa

```python
from utils.enviar_correo import EmailWriter

m = EmailWriter()
m.conectar()                                    # SMTP + EHLO + STARTTLS + login
m.enviar()                                      # usa ASUNTO y TEXTO de env
m.enviar("asunto custom", "cuerpo custom")      # override por llamada
m.enviar("html", "<b>negrita</b>", html=True)   # cuerpo HTML
m.cerrar()                                      # quit() del server
```

`EmailWriter` también es context manager (`__enter__`/`__exit__`) — `with EmailWriter() as m:` equivale a instanciar, conectar manualmente y llamar `cerrar()` al final.

### Ejemplo real: daemon que consume los JSON de `error_system.py`

```python
# mi_daemon/main.py — corre en bucle, lee errores/ y manda cada uno por email
import glob
import os
import time
from dotenv import load_dotenv

from utils.enviar_correo import EmailWriter
from utils.json_writer import JsonFileWriter

load_dotenv()

CARPETA_ERRORES = os.getenv("CARPETA_ERRORES", "./notificaciones/")

def procesar_errero(ruta_json: str, m: EmailWriter) -> None:
    payload = JsonFileWriter(ruta_json).read()
    if not payload or not payload.get("errores"):
        return
    for err in payload["errores"]:
        notif = err.get("notificacion", {})
        if not notif.get("email"):
            continue
        cuerpo = f"[{err['tipo'].upper()}] {err['texto']}\n\nContexto: {err.get('contexto')}"
        m.enviar(
            asunto=f"[{payload.get('origen')}] {err['tipo']}: {err['texto'][:50]}",
            cuerpo=cuerpo,
        )
    os.remove(ruta_json)                # marca como procesado

def main():
    with EmailWriter() as m:
        m.conectar()
        while True:
            for ruta in glob.glob(os.path.join(CARPETA_ERRORES, "errores_*.json")):
                try:
                    procesar_errero(ruta, m)
                except Exception as e:
                    print(f"fallo procesando {ruta}: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()
```

### Ejemplo real: envío directo (un solo correo desde un script)

```python
# mi_script/main.py
from utils.enviar_correo import EmailWriter

with EmailWriter() as m:
    m.conectar()
    m.enviar(
        asunto="reporte diario",
        cuerpo="<h1>OK</h1><p>todo fue bien</p>",
        html=True,
    )
```

### Ejemplo real: docker entrypoint (migración del antiguo `envio_correo_docker`)

El antiguo `envio_correo_docker/Dockerfile` ahora apunta a `../utils/enviar_correo.py` y se construye con `docker build` desde la raíz del repo. El entrypoint sigue siendo el mismo:

```bash
docker build -t correo-docker /workspace/utilidades_python/
docker run --rm \
  -e EMISOR_CORREO=tu_correo@gmail.com \
  -e PASS_CORREO=tu_app_password \
  -e RECEPTOR_CORREO=dest@x.com \
  -e ASUNTO="UPS ALERTA" \
  -e TEXTO="UPS ha cambiado de estado" \
  correo-docker
```

Igual que antes, pero ahora `enviar_correo.py` también se puede importar como utilidad Python normal desde otro proyecto.

### Errores comunes

- **Usar la password normal de Gmail en vez de app password** → Google la rechaza. Genera una en [https://myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords) y úsala como `PASS_CORREO`.
- **Olvidar `SMTP_HOST`/`SMTP_PORT`** → tienen defaults (`smtp.gmail.com` / `587`) pero si tu proveedor usa otro (Outlook, Sendgrid, Mailgun) ponlos en env.
- **Confundir `html=False` con pasar HTML en el cuerpo** → si el cuerpo es `<b>hola</b>` y `html=False`, se envía literal como texto. Pon `html=True` para que se renderice.
- **Llamar `enviar()` antes de `conectar()`** → lanza `RuntimeError`. Siempre: `conectar()` → `enviar()` → `cerrar()` (o usa el `with`).
- **Olvidar `cerrar()` sin context manager** → la conexión SMTP queda abierta. Usa `with EmailWriter() as m:` para evitarlo.
- **Asumir que el subject es opcional** → siempre se asigna `mensaje["Subject"]`. Si no pasas `asunto`, se usa el de env (o `"UPS ALERTA"` por default).

---

## enviar_notificaciones.py

### Cuándo copiarlo

- Ya produces notificaciones con `error_system.registrar_errores` y quieres un
  orquestador que las envíe por correo sin escribirlo tú
- Quieres relanzar el envío desde cron o systemd sin gestionar estado en memoria
- Necesitas un fallback para errores que el productor no supo a quién avisar
  (`EMAIL_GENERICO`)

> **Dependencia:** importa `enviar_correo.EmailWriter`, `json_writer.JsonFileWriter`
> y `error_system.envio_control`. Copia los cuatro archivos juntos. Ver
> [Dependencias entre utilidades](#dependencias-entre-utilidades).

### Configuración (.env)

```bash
# Las credenciales SMTP las toma de enviar_correo (EMISOR_CORREO, PASS_CORREO,
# SMTP_HOST, SMTP_PORT). Si no las seteas, el daemon se queja y no procesa.
EMAIL_GENERICO=alertas@midominio.com         # To por defecto si un error no trae to_email
CARPETA_ERRORES=./notificaciones/             # Donde están los errores_*.json pendientes
ENVIADOS_DIR=./notificaciones/enviados/       # Tras procesar, los mueve aquí (se crea sola)
RETENCION_HORAS=24                            # Horas en enviados/ antes de borrarse
# Log: RUTA_CONTROL, LOG_NIVEL, ... (heredados de error_system)
```

### API mínima

```bash
# desde CLI
python -m utils.enviar_notificaciones
# o desde un script
python utils/enviar_notificaciones.py
```

```python
from utils.enviar_notificaciones import procesar

res = procesar()
# res = {"borrados": int, "ficheros": int, "enviados": int, "fallidos": int, "sin_dest": int}
```

### Qué hace una pasada (`procesar()`)

1. **Limpieza previa.** Borra de `ENVIADOS_DIR` los `errores_*.json` con `mtime` más
   viejo que `ahora - RETENCION_HORAS*3600`. Una syscall por fichero.
2. **Sin pendientes → sale.** Si no hay `errores_*.json` en `CARPETA_ERRORES`, no
   abre SMTP y devuelve un resumen con ceros.
3. **Sin credenciales → se queja.** Si falta `EMISOR_CORREO` o `PASS_CORREO`,
   loguea ERROR con `envio_control` y sale **sin mover** los pendientes (los deja
   para la siguiente, cuanto tengas creds).
4. **Conexión SMTP.** `with EmailWriter() as m: m.conectar()`.
5. **Por cada fichero JSON** (orden alfabético):
   - Lee el payload con `JsonFileWriter`. Si está corrupto o no se puede leer,
     lo mueve a `ENVIADOS_DIR` igual (no dejamos basura pudriéndose en cola).
   - Por cada `error` con `notificacion.email == True`:
     - `To` = `error.to_email` (schema v1.1) si existe, si no `EMAIL_GENERICO`.
       Si no hay ninguno → log WARNING, cuenta `sin_dest` y skip este error.
     - `From` = `EMISOR_CORREO` (siempre; el login SMTP es el remitente).
     - `Asunto` = `[<origen>] <TIPO>: <texto[:50]>`.
     - `Cuerpo` = `[TIPO] texto\n\nOrigen: <origen>\nContexto: <contexto>`.
     - `m.enviar(...)`. Si falla, log ERROR, cuenta `fallidos`, **continúa** con
       el resto (un fallo de SMTP no aborta el lote).
   - Mueve el fichero procesado a `ENVIADOS_DIR` con `shutil.move`.
6. **Resume** con `envio_control`: `ficheros X, enviados Y, fallidos Z, sin_dest W`.

### Ejemplo real: cron cada 5 minutos

```cron
# crontab -e
*/5 * * * *  cd /app && /usr/bin/python -m utils.enviar_notificaciones
```

El script es one-shot, así que cron es el bucle. No hay señales que manejar, no
hay estado en memoria. Si una pasada tarda más de 5 minutos, la siguiente se
encola (cron ya lo gestiona). En systemd timer:

```ini
# /etc/systemd/system/enviar-notificaciones.service
[Service]
WorkingDirectory=/app
ExecStart=/usr/bin/python -m utils.enviar_notificaciones
EnvironmentFile=/app/.env

# /etc/systemd/system/enviar-notificaciones.timer
[Timer]
OnBootSec=1min
OnUnitActiveSec=5min
[Install]
WantedBy=timers.target
```

### Ejemplo real: productor + daemon en el mismo proyecto

```python
# productor.py — genera errores y los deja en ./notificaciones/
from utils.error_system import nuevo_error, registrar_errores

SISTEMA = {"email": True, "log": True, "bbdd": False}
errores = []
try:
    # ... trabajo que puede fallar ...
except Exception as e:
    errores.append(nuevo_error(
        tipo="stop", texto=f"caída de servicio: {e}",
        notificar_email=True,
        to_email="oncall@midominio.com",   # este avisa a oncall
        contexto={"host": "prod-1"},
    ))

# este error NO lleva to_email; el daemon usará EMAIL_GENERICO
errores.append(nuevo_error("aviso", "memoria al 90%", notificar_email=True,
                           contexto={"host": "prod-1"}))

if errores:
    registrar_errores(SISTEMA, errores)   # origen cae a env PROYECTO
```

```bash
# daemon (cron relanza cada 5 min)
python -m utils.enviar_notificaciones
```

### Errores comunes

- **Olvidar `EMAIL_GENERICO`** → los errores sin `to_email` (la mayoría si no
  los personalizas) se cuentan como `sin_dest` y no se envían. Setea la env var
  con una dirección de ops/alertas genérica del proyecto.
- **Confundir `RECEPTOR_CORREO` con `EMAIL_GENERICO`** → `RECEPTOR_CORREO` lo
  usa `EmailWriter` directamente (un solo correo a todos). El daemon lo ignora:
  usa por-error `to_email` y cae a `EMAIL_GENERICO`. Setea `EMAIL_GENERICO`
  para el daemon, no `RECEPTOR_CORREO`.
- **Esperar reintentos** → no hay. Un envío que falla se cuenta como `fallido`
  y el JSON se mueve a `enviados/` igual. Si necesitas reintentos, bloquea el
  move en `_procesar_fichero` o monta tu lógica aparte.
- **Mover antes de confirmar el envío** → el daemon m pasa tras procesar el
  fichero completo (haya fallado o no todos sus errores). Si el proceso muere
  a mitad, el JSON se queda en pendientes y se reintentará entero en la siguiente
  pasada (idempotente: el destinatario puede recibir duplicados).
- **Poner `CARPETA_ERRORES` apuntando a `enviados/`** → loop. Setea una carpeta
  pendientes y otra `ENVIADOS_DIR` distinta (los defaults ya lo hacen bien).
- **Esperar que se borre nada en la primera pasada** → los ficheros recién
  movidos a `enviados/` tienen `mtime = ahora`. Tienen que cumplir >24h antes
  del borrado (siguiente pasada, un día después).

---

## check_updates.py

### Cuándo copiarlo

Tienes 2+ proyectos con copias de las utilidades y quieres saber cuáles están desactualizados.

**No lo copies a tus proyectos destino**: es una herramienta de mantenimiento que se ejecuta desde este repo (o una copia) contra tus proyectos. Si quieres automatizar, puedes copiarlo, pero no es su uso principal.

### Instalación

Vive en `utils/check_updates.py` dentro de este repo. Para usarlo en otra máquina, copia el archivo (es autocontenido, solo stdlib) y ejecútalo con `python utils/check_updates.py`.

### Uso básico

```bash
python utils/check_updates.py <directorio_utils_origen> <directorio_utils_destino>
```

Donde:

- `directorio_utils_origen` = ruta al `utils/` de este repo (donde están los `.py` con `__version__`)
- `directorio_utils_destino` = ruta al `utils/` de tu proyecto (o donde hayas copiado los archivos)

### Ejemplo: chequear un proyecto

```bash
$ python utils/check_updates.py /workspace/utilidades_python/utils/ ~/work/mi_app/utils/

Origen:  /workspace/utilidades_python/utils
Destino: /home/user/work/mi_app/utils

  archivo           origen      destino     estado
  ------------------------------------------------
  csv_writer.py     1.0.0       1.0.0       OK
  error_system.py   2.0.0       —           FALTA_EN_DESTINO
  json_writer.py    1.0.0       0.9.0       DESACTUALIZADO
  text_writer.py    1.0.1       1.0.0       DESACTUALIZADO
  time_utils.py     1.0.0       1.0.0       OK

Resumen: 3 OK, 2 desactualizados, 1 falta
Exit: 1
```

### Ejemplo: chequear varios proyectos

```bash
$ for proj in ~/work/*/; do
    echo "### $proj ###"
    python utils/check_updates.py /workspace/utilidades_python/utils/ "$proj/utils/"
  done

### /home/user/work/app_a/ ###
Origen:  ...
Destino: ...
  ...
Resumen: 6 OK
Exit: 0

### /home/user/work/app_b/ ###
Origen:  ...
Destino: ...
  ...
Resumen: 4 OK, 1 desactualizado, 1 falta
Exit: 1
```

### Interpretación de estados

| Estado | Significado | Acción |
|---|---|---|
| `OK` | Versión idéntica | Ninguna |
| `DESACTUALIZADO` | Destino tiene versión menor | Copia el archivo desde el origen |
| `FALTA_EN_DESTINO` | El origen tiene este archivo, el destino no | Cópialo al destino |
| `MAS_NUEVO_EN_DESTINO` | Destino tiene versión mayor | Probablemente intencional (customización local). Verificar |
| `SIN_VERSION` | Archivo destino no tiene `__version__` | Reemplaza el archivo desde el origen |

### Exit codes

- `0` — todo actualizado
- `1` — hay desactualizados, faltan archivos o no tienen `__version__`
- `2` — error de argumentos o rutas no existen (no se imprime la tabla)

Útil para integrar en scripts o CI:

```bash
if python utils/check_updates.py /workspace/utilidades_python/utils/ ~/work/mi_app/utils/; then
    echo "todo actualizado"
else
    echo "hay que actualizar algo"
fi
```

### Sin argumentos: self-check

Si lo ejecutas sin argumentos, corre el self-check integrado:

```bash
$ python utils/check_updates.py
# ... (corre tests internos) ...
check_updates v1.0.0 OK
```

### Errores comunes

- **Pasar la raíz del proyecto en vez de `utils/`** → `check_updates` compara archivos `.py` directamente. Si pasas `~/work/mi_app/`, mirará los `.py` de la raíz del proyecto, no los de `utils/`. Pasa siempre la carpeta concreta.
- **Pasar este repo sin el sufijo `/utils/`** → ahora los `.py` viven en `utils/`, así que el origen debe apuntar a `utils/` también: `/workspace/utilidades_python/utils/`. Si pasas solo `/workspace/utilidades_python/`, no encontrará ningún `.py`.
- **Rutas con espacios sin comillas** → `"~/work/mi app/utils/"` debe ir entre comillas dobles en el shell, sino se corta en el espacio.
- **Path absoluto vs relativo** → `check_updates` normaliza a absoluto con `os.path.abspath`, así que puedes mezclar. Pero para que la salida sea legible, pasa absolutos.
- **Esperar que actualice automáticamente** → por diseño NO copia. Solo informa. La copia es decisión tuya (consciente).
