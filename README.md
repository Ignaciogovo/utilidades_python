# utilidades-python

Librería raíz de utilidades Python reutilizables, pensada para copiarse archivo a archivo en distintos proyectos personales.

## Qué hay aquí

| Archivo | Versión | Para qué sirve | Cuándo copiarlo |
|---|---|---|---|
| `csv_writer.py` | 1.0.0 | Leer/escribir CSV con control de cabeceras y modos (`w`/`a`) | Siempre que escribas CSVs a fichero |
| `text_writer.py` | 1.0.0 | Leer/escribir ficheros de texto plano con append limpio | Cuando necesites logs o `.txt` simples |
| `json_writer.py` | 1.0.0 | Leer/escribir JSON creando carpetas padre y con append dict/list | Cuando persistas estado o config en JSON |
| `error_schema.py` | 1.0.0 | Constantes y validación del schema JSON v1 de errores | Con `error_manager` (no se usa solo) |
| `error_manager.py` | 1.0.0 | `nuevo_error()` + `registrar_errores()` que produce JSON para un daemon externo | Cuando quieras registrar errores y que otro proceso los consuma |
| `check_updates.py` | 1.0.0 | Compara versiones entre este repo y un proyecto destino | Cuando tengas 2+ proyectos con copias de las utilidades |

Todos los `.py` tienen un **self-check ejecutable**: `python nombre_archivo.py`.

## Cómo usarlo en otro proyecto

### Paso 1 — Identifica qué necesitas

Mira la tabla de arriba y decide qué archivos te interesan. No hace falta copiarlos todos.

### Paso 2 — Crea la carpeta de utilidades

Convención recomendada: `utils/` en la raíz de tu proyecto.

```
mi_proyecto/
├── main.py
├── utils/                 ← aquí dentro
│   ├── csv_writer.py
│   └── error_manager.py
└── ...
```

### Paso 3 — Copia los archivos

Copia los `.py` desde este repo a `utils/` de tu proyecto.

### Paso 4 — Comprueba la versión

La versión está en la cabecera de cada archivo (línea 2 o 3):

```python
# utilidades-python:csv_writer
# Descripción: Escritura/lectura simple de CSV con control de cabeceras y modos
# __version__ = "1.0.0"
```

Compara la versión de tu copia con la de este repo (mira la tabla "Changelog" abajo o el README más reciente). Si hay diferencia, copia la versión actualizada.

### Paso 5 — Importa en tu código

```python
from utils.csv_writer import CSVWriter, exportar_csv
from utils.error_manager import nuevo_error, registrar_errores
```

### Paso 6 — Configura la carpeta de errores (opcional)

Si usas `error_manager.py`, define en tu `.env`:

```bash
CARPETA_ERRORES=/var/log/mi_proyecto/errores
```

Si no la defines, usa `./errores/` por defecto.

## Cómo comprobar actualizaciones en tus proyectos

`check_updates.py` compara dos directorios (origen = este repo, destino = `utils/` de un proyecto) y reporta el estado de cada utilidad.

### Un proyecto

```bash
python check_updates.py /workspace/utilidades_python/ ~/work/mi_proyecto/utils/
```

### Varios proyectos

```bash
for proj in ~/work/*/; do
  python check_updates.py /workspace/utilidades_python/ "$proj/utils/"
done
```

### Salida

```
Origen:  /workspace/utilidades_python
Destino: /home/user/work/mi_proyecto/utils

  archivo           origen      destino     estado
  ------------------------------------------------
  csv_writer.py     1.0.0       1.0.0       OK
  error_manager.py  1.0.0       —           FALTA_EN_DESTINO
  json_writer.py    1.0.0       0.9.0       DESACTUALIZADO

Resumen: 1 OK, 1 desactualizado, 1 falta
```

### Estados posibles

- `OK` — versión idéntica
- `DESACTUALIZADO` — el destino tiene versión menor → copia el archivo desde el origen
- `FALTA_EN_DESTINO` — el origen tiene este archivo, el destino no → cópialo
- `MAS_NUEVO_EN_DESTINO` — el destino tiene versión mayor (puede ser intencional, ej. una customización local)
- `SIN_VERSION` — el archivo destino no tiene `__version__` → reescríbelo desde el origen

### Exit codes

- `0` — todo actualizado
- `1` — hay desactualizados, faltan archivos o no tienen `__version__`
- `2` — error de argumentos o rutas no existen

## Ejemplo completo de uso

```python
# main.py de tu proyecto
from datetime import date
from utils.csv_writer import exportar_csv
from utils.error_manager import nuevo_error, registrar_errores

sistema = {"email": True, "log": True, "bbdd": False}
errores = []

try:
    exportar_csv(
        filename="/data/reporte_hoy.csv",
        datos=[str(date.today()), "42", "ok"],
        cabecera=["fecha", "valor", "estado"],
        modo="sobrescribir",
    )
except Exception as e:
    errores.append(nuevo_error(
        tipo="aviso",
        texto=f"Fallo al escribir CSV: {e}",
        notificar_email=True,
        notificar_log=True,
    ))

if errores:
    registrar_errores(sistema, errores, origen="mi_proyecto")
```

## Schema JSON v1 de errores

Este es el formato que produce `error_manager.py` y que consumirá el daemon externo:

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

## Convención de versionado

SemVer simple:

- `MAJOR` (1.0.0 → 2.0.0) — cambia la API pública, no es drop-in
- `MINOR` (1.0.0 → 1.1.0) — añade método o función compatible con la API existente
- `PATCH` (1.0.0 → 1.0.1) — fix de bug sin cambios de API

`check_updates.py` usa comparación numérica de tuplas: `tuple(int(x) for x in v.split("."))`. No valida que sea SemVer estricto, solo que el formato sea `X.Y.Z`.

## Changelog

### 1.0.0 (inicial)

- `csv_writer.py` — `CSVWriter` (write/add_row/clear/is_empty/read_all) + `exportar_csv` (wrapper de un solo uso)
- `text_writer.py` — `TextFileWriter` (write/add_line/clear/read_all)
- `json_writer.py` — `JsonFileWriter` (write/read/append con creación de carpetas)
- `error_schema.py` — `SCHEMA_VERSION`, `TIPOS_VALIDOS`, `validate_error()`
- `error_manager.py` — `nuevo_error()` (fábrica) + `registrar_errores()` (filtra y escribe JSON)
- `check_updates.py` — comparador origen/destino con self-check y CLI

## Lo que NO hace este repo

- **No envía correos**. El envío de correo es responsabilidad del daemon que consuma los JSON
- **No escribe en BBDD**. Mismo motivo
- **No es un paquete pip**. Se copia archivo a archivo, no se instala
- **No tiene tests con pytest**. Cada archivo tiene un self-check ejecutable que verifica la lógica principal
