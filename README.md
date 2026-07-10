# utilidades-python

Librería raíz de utilidades Python reutilizables, pensada para copiarse archivo a archivo en distintos proyectos personales.

> **¿Overview rápido o tutorial profundo?**
> - Estás en el **README** (overview, tabla, 8 pasos para empezar, API resumida, schema, changelog)
> - Para tutorial detallado por utilidad (instalación, API completa, ejemplos reales, errores comunes), mira **[TUTORIAL.md](TUTORIAL.md)**
>
> `check_updates.py` para mantenimiento entre proyectos → también cubierto en TUTORIAL.md

## Qué hay aquí

| Archivo | Versión | Para qué sirve | Cuándo copiarlo |
|---|---|---|---|
| `csv_writer.py` | 1.0.0 | Leer/escribir CSV con control de cabeceras y modos (`w`/`a`) | Siempre que escribas CSVs a fichero |
| `text_writer.py` | 1.0.1 | Leer/escribir ficheros de texto plano con append limpio (sin `\n` espurio en archivo nuevo) | Cuando necesites logs o `.txt` simples |
| `json_writer.py` | 1.0.0 | Leer/escribir JSON creando carpetas padre y con append dict/list | Cuando persistas estado o config en JSON |
| `error_system.py` | 1.0.0 | Sistema unificado de errores y logs: validación, fabricación, registro a JSON, trazas de control, consulta por clave | Cuando quieras registrar errores y/o dejar trazas de control |
| `time_utils.py` | 1.0.0 | Conversión entre `date` y strings `YYYYMMDD` (compacto) / `YYYY-MM-DD` (extendido) y validación | Cuando manejes fechas en formato compacto |
| `check_updates.py` | 1.0.0 | Compara versiones entre este repo y un proyecto destino | Cuando tengas 2+ proyectos con copias de las utilidades |

Todos los `.py` tienen un **self-check ejecutable**: `python nombre_archivo.py`.

## Cómo usarlo en un proyecto real (paso a paso)

Ejemplo: quieres añadir estas utilidades a un proyecto que ya tienes (`mi_proyecto/`). El proyecto es un scraper que cada día descarga datos y los guarda en CSVs, y quieres registrar errores y trazas.

### 1. Identifica qué necesitas

Para este ejemplo necesitas: `csv_writer.py`, `text_writer.py`, `json_writer.py`, `error_system.py`. No necesitas `time_utils` ni `check_updates` (este último solo lo usas TÚ, el desarrollador, no el proyecto).

### 2. Prepara la estructura del proyecto

```
mi_proyecto/
├── .env                          # variables de entorno (no commitear)
├── main.py                       # tu programa principal
├── utils/                        # aquí van las utilidades copiadas
│   ├── csv_writer.py
│   ├── text_writer.py
│   ├── json_writer.py
│   └── error_system.py
└── ...
```

Crea la carpeta `utils/` (vacía por ahora).

### 3. Copia los archivos desde este repo

```bash
cp /workspace/utilidades_python/csv_writer.py   mi_proyecto/utils/
cp /workspace/utilidades_python/text_writer.py  mi_proyecto/utils/
cp /workspace/utilidades_python/json_writer.py  mi_proyecto/utils/
cp /workspace/utilidades_python/error_system.py mi_proyecto/utils/
```

### 4. Verifica versiones

Abre cualquiera de los archivos copiados, mira la cabecera:

```python
# utilidades-python:csv_writer
# Descripción: Escritura/lectura simple de CSV con control de cabeceras y modos
# __version__ = "1.0.0"
```

Compara con la tabla de arriba. Si tu versión es menor, copia el archivo actualizado.

### 5. Configura el `.env` del proyecto

```bash
# .env (en la raíz de mi_proyecto, NO commitear)
CARPETA_ERRORES=/var/log/mi_proyecto/errores
RUTA_CONTROL=/var/log/mi_proyecto/control.txt
```

Carga el `.env` con `python-dotenv` (o como prefieras):

```python
from dotenv import load_dotenv
load_dotenv()
```

### 6. Escribe tu `main.py`

```python
# main.py
import time
from datetime import date
from dotenv import load_dotenv

from utils.csv_writer import exportar_csv
from utils.text_writer import TextFileWriter
from utils.error_system import (
    nuevo_error,
    registrar_errores,
    envio_control,
    fdatos_keys_errores,
    validar_error,
)
from utils.time_utils import convert_fecha_en_str, es_fecha_valida

load_dotenv()

SISTEMA = {"email": True, "log": True, "bbdd": False}
errores = []

envio_control(f"=== Inicio {date.today()} ===")

# --- lógica del proyecto ---
inicio = time.time()
hoy_str = convert_fecha_en_str(date.today())
archivo = f"/data/scraper_{hoy_str}.csv"
cabecera = ["fecha", "valor", "estado"]

try:
    envio_control("Descargando datos...")
    # ... tu lógica real ...
    datos = [str(date.today()), "42", "ok"]
    exportar_csv(archivo, datos, cabecera, modo="sobrescribir")
    envio_control("CSV escrito correctamente")

except Exception as e:
    errores.append(nuevo_error(
        tipo="aviso",
        texto=f"Fallo al procesar: {e}",
        notificar_email=True,
        notificar_log=True,
        contexto={"fichero": archivo},
    ))

duracion = time.time() - inicio
envio_control(f"Duración: {duracion:.2f}s")

# --- al final del proceso, vuelca errores a JSON para el daemon ---
if errores:
    tipos = fdatos_keys_errores(errores, "tipo")
    envio_control(f"Registrando {len(errores)} errores, tipos: {tipos}")
    ruta = registrar_errores(SISTEMA, errores, origen="mi_proyecto_scraper")
    envio_control(f"Errores escritos en: {ruta}")
else:
    envio_control("Sin errores")

envio_control("=== Fin ===")
```

### 7. Repite en cada proyecto

Cada vez que empieces un proyecto nuevo:

1. Decide qué archivos necesitas (la mayoría usa los 4 mismos)
2. Cópialos a `utils/`
3. Configura las env vars en el `.env` del proyecto
4. Importa y a funcionar

### 8. Mantenimiento: detecta actualizaciones

Cuando pasen semanas, puede que este repo tenga versiones nuevas. Ejecuta:

```bash
python check_updates.py /workspace/utilidades_python/ ~/work/mi_proyecto/utils/
```

Si hay `DESACTUALIZADO` o `FALTA_EN_DESTINO`, copia el archivo actualizado.

Para chequear varios proyectos de golpe:

```bash
for proj in ~/work/*/; do
  echo "--- $proj ---"
  python check_updates.py /workspace/utilidades_python/ "$proj/utils/"
done
```

## API de las utilidades

### `error_system` (módulo unificado)

```python
from utils.error_system import (
    nuevo_error,
    registrar_errores,
    envio_control,
    fdatos_keys_errores,
    validar_error,
    SCHEMA_VERSION,
    TIPOS_VALIDOS,
)

# fabricar error
err = nuevo_error(
    tipo="aviso",                       # "aviso" | "stop" | "info"
    texto="descripción legible",
    notificar_email=True,
    notificar_log=True,
    notificar_bbdd=False,
    contexto={"jornada": 12, "equipo": "X"},
)

# validar contra schema v1
if not validar_error(err):
    raise ValueError("error mal formado")

# consultar por clave
tipos = fdatos_keys_errores(lista_errores, "tipo")     # ["aviso", "stop", ...]
dias  = fdatos_keys_errores(lista_errores, "dia")      # ["2026-07-10", ...]

# registrar y volcar a JSON (un fichero por llamada)
ruta = registrar_errores(
    sistema={"email": True, "log": True, "bbdd": False},
    errores=lista_errores,
    origen="mi_proyecto",
    carpeta=None,                       # None → usa env CARPETA_ERRORES o "./errores/"
)

# trazas de control (log de ejecución)
envio_control("inicio del proceso")     # append a RUTA_CONTROL
```

### `time_utils`

```python
from utils.time_utils import (
    convert_str_en_fecha,               # "YYYYMMDD" → date
    convert_fecha_en_str,               # date → "YYYYMMDD"
    es_fecha_valida,                    # date o "YYYY-MM-DD" → bool
)

d = convert_str_en_fecha("20260710")    # date(2026, 7, 10)
s = convert_fecha_en_str(d)             # "20260710"

es_fecha_valida("2026-07-10")           # True
es_fecha_valida("20260710")             # False (formato compacto no soportado aquí)
es_fecha_valida("2026-13-40")           # False
```

**Nota sobre formatos**: `convert_*` usan **compacto** `YYYYMMDD`; `es_fecha_valida` acepta objetos `date` o strings **extendidos** `YYYY-MM-DD`. Si necesitas validar un string compacto, conviértelo primero con `convert_str_en_fecha` y captura la excepción.

### `csv_writer`

```python
from utils.csv_writer import CSVWriter, exportar_csv

# Clase con estado
w = CSVWriter("/data/x.csv", ["col1", "col2"])
w.write_data(["v1", "v2"])             # crea / sobrescribe, escribe cabecera + fila
w.add_row(["v3", "v4"])                # anexa fila
w.read_all()                           # [{"col1": "v1", "col2": "v2"}, ...]
w.is_empty_csv()                       # bool
w.clear_file()                         # vacía

# Wrapper de un solo uso
exportar_csv("/data/x.csv", ["v1"], cabecera=["c1"], modo="sobrescribir")  # bool
exportar_csv("/data/x.csv", ["v2"], cabecera=["c1"], modo="anexar")        # bool
```

### `text_writer`

```python
from utils.text_writer import TextFileWriter

w = TextFileWriter("/data/x.txt")
w.write_data("texto inicial")          # crea / sobrescribe
w.add_line("segunda línea")            # append limpio (añade \n solo si el archivo no está vacío)
w.read_all()                           # "texto inicial\nsegunda línea"
w.clear_file()                         # vacía
```

### `json_writer`

```python
from utils.json_writer import JsonFileWriter

w = JsonFileWriter("/data/x.json")
w.write({"a": 1, "b": [1, 2, 3]})      # sobrescribe, crea carpetas padre
w.read()                               # {'a': 1, 'b': [1, 2, 3]} o None
w.append({"c": "nuevo"})               # carga, hace update (dict) o extend (list), reescribe
```

### `check_updates`

```bash
python check_updates.py <origen> <destino>
```

Estados posibles: `OK` / `DESACTUALIZADO` / `FALTA_EN_DESTINO` / `MAS_NUEVO_EN_DESTINO` / `SIN_VERSION`.

Exit codes: `0` todo OK, `1` hay problemas, `2` error de argumentos o rutas.

## Schema JSON v1 de errores

Este es el formato que produce `registrar_errores()` y que consumirá el daemon externo:

```json
{
  "schema_version": "1.0",
  "timestamp_creacion": "2026-07-10T09:30:00",
  "origen": "nombre_proyecto_o_proceso",
  "errores": [
    {
      "tipo": "aviso | stop | info",
      "texto": "descripción legible del error",
      "timestamp": "2026-07-10T09:25:00",
      "dia": "2026-07-10",
      "notificacion": {
        "email": true,
        "log": true,
        "bbdd": false
      },
      "contexto": { "cualquier_campo_extra": "..." }
    }
  ]
}
```

El campo `contexto` es el punto de extensión: cada proyecto añade aquí sus datos específicos (jornada, temporada, partido, etc.) sin romper el schema.

Cada llamada a `registrar_errores()` produce **un fichero por timestamp**: `errores_YYYYMMDD_HHMMSS.json` dentro de `CARPETA_ERRORES` (o `./errores/`). El daemon los procesa y los puede borrar o archivar.

## Convención de versionado

SemVer simple:

- `MAJOR` (1.0.0 → 2.0.0) — cambia la API pública, no es drop-in
- `MINOR` (1.0.0 → 1.1.0) — añade método o función compatible con la API existente
- `PATCH` (1.0.0 → 1.0.1) — fix de bug sin cambios de API

`check_updates.py` usa comparación numérica de tuplas: `tuple(int(x) for x in v.split("."))`. No valida que sea SemVer estricto, solo que el formato sea `X.Y.Z`.

## Changelog

### 1.0.0 — inicial

- `csv_writer.py` v1.0.0 — `CSVWriter` (write/add_row/clear/is_empty/read_all) + `exportar_csv` (wrapper de un solo uso)
- `text_writer.py` v1.0.0 — `TextFileWriter` (write/add_line/clear/read_all)
- `text_writer.py` v1.0.1 — fix: `add_line` ya no añade `\n` espurio cuando el archivo no existe
- `json_writer.py` v1.0.0 — `JsonFileWriter` (write/read/append con creación de carpetas)
- `error_system.py` v1.0.0 — sistema unificado: `validar_error`, `nuevo_error`, `fdatos_keys_errores`, `registrar_errores`, `envio_control`
- `time_utils.py` v1.0.0 — `convert_str_en_fecha`, `convert_fecha_en_str`, `es_fecha_valida`
- `check_updates.py` v1.0.0 — comparador origen/destino con self-check y CLI
- `README.md` — overview, tabla, 8 pasos, API resumida, schema, changelog
- `TUTORIAL.md` — guía detallada por utilidad: instalación, API completa, ejemplos reales, errores comunes

## Lo que NO hace este repo

- **No envía correos**. El envío de correo es responsabilidad del daemon que consuma los JSON
- **No escribe en BBDD**. Mismo motivo
- **No es un paquete pip**. Se copia archivo a archivo, no se instala
- **No tiene tests con pytest**. Cada archivo tiene un self-check ejecutable que verifica la lógica principal
