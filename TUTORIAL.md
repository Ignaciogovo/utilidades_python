# Tutorial de uso por utilidad

Guía detallada, una sección por archivo `.py`, con ejemplos prácticos para casos reales. Si solo quieres el overview + cómo empezar, mira `README.md`. Este documento es la referencia profunda.

Índice:

- [csv_writer.py](#csv_writerpy)
- [text_writer.py](#text_writerpy)
- [json_writer.py](#json_writerpy)
- [error_system.py](#error_systempy)
- [time_utils.py](#time_utilspy)
- [check_updates.py](#check_updatespy)

---

## csv_writer.py

### Cuándo copiarlo a tu proyecto

- Generas reportes en CSV (scrapers, exports de BBDD, listados)
- Necesitas anexar filas a un CSV existente sin romper la cabecera
- Quieres leer un CSV como lista de dicts

### Instalación

Copia el archivo a `utils/` de tu proyecto:

```bash
cp /workspace/utilidades_python/csv_writer.py mi_proyecto/utils/
```

No tiene dependencias externas. Solo stdlib (`csv`, `os`).

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

### Instalación

```bash
cp /workspace/utilidades_python/text_writer.py mi_proyecto/utils/
```

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

### Instalación

```bash
cp /workspace/utilidades_python/json_writer.py mi_proyecto/utils/
```

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

### Instalación

```bash
cp /workspace/utilidades_python/error_system.py mi_proyecto/utils/
```

Requiere también `json_writer.py` y `text_writer.py` (los importa).

### Configuración (.env)

```bash
CARPETA_ERRORES=/var/log/mi_proyecto/errores
RUTA_CONTROL=/var/log/mi_proyecto/control.txt
```

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
    nuevo_error,        # fábrica de dicts
    validar_error,      # valida contra schema v1
    fdatos_keys_errores, # extrae una clave de cada error
    registrar_errores,  # filtra y escribe JSON
    envio_control,      # trazas a fichero de control
    SCHEMA_VERSION,
    TIPOS_VALIDOS,
)

# fabricar
err = nuevo_error(
    tipo="stop",                      # "aviso" | "stop" | "info"
    texto="jornada incompleta",
    notificar_email=True,
    notificar_log=True,
    notificar_bbdd=False,
    contexto={"jornada": 12, "temporada": 2026},
)

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
    origen="mi_proyecto",          # aparece en el JSON, útil para el daemon
    carpeta=None,                  # None = usa env CARPETA_ERRORES o "./errores/"
)
# ruta → "/var/log/.../errores/errores_20260710_120000.json" o None si no había nada

# trazas de control (logs de ejecución)
envio_control("inicio")            # append a RUTA_CONTROL
envio_control("fin")
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

---

## time_utils.py

### Cuándo copiarlo

- Tu sistema usa formato compacto `YYYYMMDD` para nombres de archivo o claves (común en legacy, SAP, ciertos APIs)
- Necesitas conversión bidireccional `date` ↔ string
- Validas fechas de input que pueden venir en distintos formatos

### Instalación

```bash
cp /workspace/utilidades_python/time_utils.py mi_proyecto/utils/
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

## check_updates.py

### Cuándo copiarlo

Tienes 2+ proyectos con copias de las utilidades y quieres saber cuáles están desactualizados.

**No lo copies a tus proyectos destino**: es una herramienta de mantenimiento que se ejecuta desde este repo (o una copia) contra tus proyectos. Si quieres automatizar, puedes copiarlo, pero no es su uso principal.

### Instalación

No requiere instalación. Ya está en la raíz de este repo. Para usarlo en otra máquina, copia `check_updates.py` (es autocontenido, solo stdlib).

### Uso básico

```bash
python check_updates.py <directorio_origen> <directorio_destino>
```

Donde:

- `directorio_origen` = ruta a este repo (donde están los `.py` con `__version__`)
- `directorio_destino` = ruta al `utils/` de tu proyecto (o donde hayas copiado los archivos)

### Ejemplo: chequear un proyecto

```bash
$ python check_updates.py /workspace/utilidades_python/ ~/work/mi_app/utils/

Origen:  /workspace/utilidades_python
Destino: /home/user/work/mi_app/utils

  archivo           origen      destino     estado
  ------------------------------------------------
  csv_writer.py     1.0.0       1.0.0       OK
  error_system.py   1.0.0       —           FALTA_EN_DESTINO
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
    python check_updates.py /workspace/utilidades_python/ "$proj/utils/"
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
if python check_updates.py /workspace/utilidades_python/ ~/work/mi_app/utils/; then
    echo "todo actualizado"
else
    echo "hay que actualizar algo"
fi
```

### Sin argumentos: self-check

Si lo ejecutas sin argumentos, corre el self-check integrado:

```bash
$ python check_updates.py
# ... (corre tests internos) ...
check_updates v1.0.0 OK
```

### Errores comunes

- **Pasar el directorio del proyecto en vez de `utils/`** → `check_updates` compara archivos `.py` directamente. Si pasas `~/work/mi_app/`, mirará los `.py` de la raíz del proyecto, no los de `utils/`. Pasa siempre la carpeta concreta.
- **Rutas con espacios sin comillas** → `"~/work/mi app/utils/"` debe ir entre comillas dobles en el shell, sino se corta en el espacio.
- **Path absoluto vs relativo** → `check_updates` normaliza a absoluto con `os.path.abspath`, así que puedes mezclar. Pero para que la salida sea legible, pasa absolutos.
- **Esperar que actualice automáticamente** → por diseño NO copia. Solo informa. La copia es decisión tuya (consciente).
