# utilidades-python

Librería raíz de utilidades Python reutilizables, pensada para copiarse archivo a archivo en distintos proyectos personales.

> **¿Overview rápido o tutorial profundo?**
> - Estás en el **README** (overview, quickstart, schema, convención de versionado, changelog).
> - Para tutorial detallado por utilidad (instalación, API completa, ejemplos reales, errores comunes), mira **[TUTORIAL.md](TUTORIAL.md)** — es la fuente de detalle.
>
> La guía de referencia rápida de la API para IAs vive en **[utils/GUIA_IA.md](utils/GUIA_IA.md)**.

## Qué hay aquí

Todos los `.py` viven en `utils/`:

| Archivo | Versión | Para qué sirve | Cuándo copiarlo |
|---|---|---|---|
| `utils/csv_writer.py` | 1.0.0 | Leer/escribir CSV con control de cabeceras y modos (`w`/`a`) | Siempre que escribas CSVs a fichero |
| `utils/text_writer.py` | 1.0.1 | Leer/escribir ficheros de texto plano con append limpio (sin `\n` espurio en archivo nuevo) | Cuando necesites logs o `.txt` simples |
| `utils/json_writer.py` | 1.0.0 | Leer/escribir JSON creando carpetas padre y con append dict/list | Cuando persistas estado o config en JSON |
| `utils/error_system.py` | 2.2.1 | Sistema unificado de errores y logs: validación, fabricación, registro a JSON, trazas de control (vía stdlib `logging` con rotación temporal), consulta por clave | Cuando quieras registrar errores y/o dejar trazas de control |
| `utils/time_utils.py` | 1.0.0 | Conversión entre `date` y strings `YYYYMMDD` (compacto) / `YYYY-MM-DD` (extendido) y validación | Cuando manejes fechas en formato compacto |
| `utils/enviar_correo.py` | 1.0.0 | Envío de correo vía SMTP (Gmail por defecto) con soporte texto/HTML, lee de env vars | Cuando necesites enviar correo desde un script o un daemon |
| `utils/enviar_notificaciones.py` | 1.0.0 | Daemon one-shot que despacha los JSON de `error_system` por correo y los archiva/borra | Cuando ya produzcas notificaciones JSON y quieras un orquestador que las envíe |
| `utils/check_updates.py` | 1.0.0 | Compara versiones entre este repo y un proyecto destino | Cuando tengas 2+ proyectos con copias de las utilidades |

Todos los `.py` tienen un **self-check ejecutable**: `python -m utils.nombre_archivo` (sin args corre el self-check; con `<origen> <destino>` corre `check_updates`).

## Quickstart

Cuatro pasos; cada uno linka a la sección detallada del tutorial.

1. **[Instala las utilidades que necesitas](TUTORIAL.md#instalar-una-utilidad-en-tu-proyecto)** — copia archivo a archivo a `utils/` de tu proyecto (no es paquete pip).
   Ojo a [las dependencias](TUTORIAL.md#dependencias-entre-utilidades): `error_system` necesita `json_writer`.

2. **[Configura el `.env`](TUTORIAL.md#configuración-env)** — las utilidades leen de env vars (carpeta de errores, log de control y niveles, credenciales SMTP, etc.).

3. **[Escribe tu `main.py`](TUTORIAL.md#ejemplo-real-scraper-con-notificación)** — importa como `from utils.<utilidad> import ...` y usa. Hay ejemplos completos en TUTORIAL por cada utilidad.

4. **[Mantén tus copias actualizadas](TUTORIAL.md#comprobar-si-tus-copias-están-actualizadas)** — `python utils/check_updates.py` detecta versiones desactualizadas. Tras copiar, corre el self-check de la utilidad.

> **Receta típica:** `csv_writer` + `json_writer` + `error_system` (van juntos) cubren scraper + estado + errores + trazas. Añade `enviar_correo` si quieres despachar las alertas por email.

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

Cada llamada a `registrar_errores()` produce **un fichero por timestamp**: `errores_YYYYMMDD_HHMMSS_ffffff.json` dentro de `CARPETA_ERRORES` (default `./notificaciones/`). El daemon los procesa y los puede borrar o archivar.

## Convención de versionado

SemVer simple:

- `MAJOR` (1.0.0 → 2.0.0) — cambia la API pública, no es drop-in
- `MINOR` (1.0.0 → 1.1.0) — añade método o función compatible con la API existente
- `PATCH` (1.0.0 → 1.0.1) — fix de bug sin cambios de API

`check_updates.py` usa comparación numérica de tuplas: `tuple(int(x) for x in v.split("."))`. No valida que sea SemVer estricto, solo que el formato sea `X.Y.Z`.

## Changelog

### 2.2.1 — `_nombre_fichero_errores` con microsegundos

- `utils/error_system.py` **v2.2.1** (no breaking):
  - `_nombre_fichero_errores()` ahora usa `%Y%m%d_%H%M%S_%f` en vez de `%Y%m%d_%H%M%S`.
    Antes, dos `registrar_errores()` en el mismo segundo pisaban el mismo fichero
    (mismo timestamp → mismo filename). Con microsegundos (`%f`, 6 dígitos) colisión
    prácticamente imposible en práctica.
  - Los JSONs existentes legacy (`errores_20260710_120000.json`) siguen siendo
    legibles por `enviar_notificaciones` (el glob es `errores_*.json`).
  - No se toca el schema ni la API.

### 2.2.0 — `enviar_notificaciones` + `error_system` v2.2.0

- `utils/enviar_notificaciones.py` **v1.0.0** (nuevo): daemon one-shot para cron
  o systemd timer. Lee `errores_*.json` de `CARPETA_ERRORES`, envía los del
  canal `email` (To viene del `to_email` del error, schema v1.1, o de
  `EMAIL_GENERICO`), mueve el fichero a `ENVIADOS_DIR` y lo borra cuando han
  pasado `RETENCION_HORAS` (default 24h). Reutiliza SMTP de `enviar_correo` y
  traza en el log de control de `error_system`. Self-check sin red (stub de
  `EmailWriter`).
- `utils/error_system.py` **v2.2.0** (no breaking):
  - `registrar_errores(origen=None)` ahora cae a env var `PROYECTO` (o
    `"desconocido"`) si te lo saltas. Antes era siempre literal `"desconocido"`.
    Pasar `origen` explícito sigue ganando.
  - `nuevo_error(...)` gana `from_email` y `to_email` opcionales (CSV) — schema
    v1.1. Solo se añaden al dict del error si se pasan. `validar_error` no las
    exige (backward compatible con JSONs legacy).
- Docs (TUTORIAL, GUIA_IA, README): section nueva de `enviar_notificaciones`,
  `PROYECTO`/`EMAIL_GENERICO`/`ENVIADOS_DIR`/`RETENCION_HORAS` en el diccionario
  de env vars, dependencias actualizadas (`enviar_notificaciones` depende de
  `enviar_correo` + `json_writer` + `error_system`).

### 2.1.0 — defaults de rutas más prácticos en `error_system`

- `utils/error_system.py` **v2.1.0** (no breaking):
  - `RUTA_CONTROL` default `./control.log` → `./logs/control.log`. Los ficheros rotated por `TimedRotatingFileHandler` caen en la misma carpeta `./logs/` (se crea sola).
  - `CARPETA_ERRORES` default `./errores/` → `./notificaciones/`. El nombre de la env var no cambia (retrocompatible: si ya la seteabas, tu valor sigue ganando).
  - `enviar_correo`, `csv_writer`, `text_writer`, `json_writer`, `time_utils`, `check_updates` — sin cambios.

### 2.0.0 — `error_system` con logger profesional

- `utils/error_system.py` **v2.0.0** (breaking):
  - `envio_control` ahora usa stdlib `logging` + `TimedRotatingFileHandler`. Cada línea lleva timestamp y nivel (`2026-07-16 09:30:00,123 | INFO | msg`), en lugar de texto plano.
  - Rotación temporal automática: `LOG_ROTACION_DIAS` (default 15) + `LOG_BACKUPS` (default 4) ≈ 2 meses de retención.
  - Niveles: `envio_control("msg", nivel="DEBUG|INFO|WARNING|ERROR|CRITICAL")`. Filtrado por `LOG_NIVEL` (default `INFO`).
  - Configuración centralizada por env vars: `RUTA_CONTROL` (default `./control.log`), `LOG_NIVEL`, `LOG_ROTACION_DIAS`, `LOG_BACKUPS`, `LOG_FMT`, `LOG_CONSOLE`.
  - **Breaking**: el fichero pasa de `control.txt` (plano) a `control.log` (con timestamp/nivel). Programas que parseaban el `.txt` crudo deben adaptar el parser; la llamada `envio_control("texto")` sigue funcionando sin cambios.
  - Quitada la dependencia interna de `TextFileWriter` para el log (se sigue usando stdlib `logging`).
- `README.md` — adelgazado a overview + quickstart + schema + changelog. El detalle pasa a TUTORIAL.
- `README.md` / `TUTORIAL.md` / `utils/GUIA_IA.md` / `AGENTS.md` — actualizados con la nueva API de log y env vars.

### 1.1.0 — refactor a `utils/` + `enviar_correo`

- **Refactor**: todas las utilidades se mueven a `utils/`. El comando de `check_updates` pasa a ser `python utils/check_updates.py`. Los self-checks se invocan con `python -m utils.nombre`.
- `enviar_correo.py` v1.0.0 — `EmailWriter` (envío SMTP con STARTTLS, texto/HTML, context manager, configuración por env vars, self-check sin envío real). Adaptación al patrón utility del antiguo `envio_correo_docker/enviar_correo.py`.
- `error_system.py` — imports ajustados a relativos (`.json_writer`, `.text_writer`).
- `envio_correo_docker/Dockerfile` — actualizado para apuntar a `utils/enviar_correo.py`.
- `README.md` / `TUTORIAL.md` — rutas, índice y secciones actualizadas a la nueva estructura.

### 1.0.0 — inicial

- `utils/csv_writer.py` v1.0.0 — `CSVWriter` (write/add_row/clear/is_empty/read_all) + `exportar_csv` (wrapper de un solo uso)
- `utils/text_writer.py` v1.0.0 — `TextFileWriter` (write/add_line/clear/read_all)
- `utils/text_writer.py` v1.0.1 — fix: `add_line` ya no añade `\n` espurio cuando el archivo no existe
- `utils/json_writer.py` v1.0.0 — `JsonFileWriter` (write/read/append con creación de carpetas)
- `utils/error_system.py` v1.0.0 — sistema unificado: `validar_error`, `nuevo_error`, `fdatos_keys_errores`, `registrar_errores`, `envio_control`
- `utils/time_utils.py` v1.0.0 — `convert_str_en_fecha`, `convert_fecha_en_str`, `es_fecha_valida`
- `utils/check_updates.py` v1.0.0 — comparador origen/destino con self-check y CLI
- `README.md` — overview, tabla, 8 pasos, API resumida, schema, changelog
- `TUTORIAL.md` — guía detallada por utilidad: instalación, API completa, ejemplos reales, errores comunes

## Lo que NO hace este repo

- **No escribe en BBDD**. El registro en BBDD es responsabilidad del daemon externo que consuma los JSON.
- **No es un paquete pip**. Se copia archivo a archivo a `utils/` del proyecto destino, no se instala.
- **No tiene tests con pytest**. Cada archivo tiene un self-check ejecutable que verifica la lógica principal.
- **El envío de correo vive en una utilidad, y la lógica de despachar los JSON de `error_system.py` está en `enviar_notificaciones.py`**: `enviar_correo.py` envía un único correo (low-level, sin estado de cola); `enviar_notificaciones.py` es el daemon one-shot que lee los JSON pendientes, los despacha con `EmailWriter`, los archiva en `enviados/` y los borra tras 24h. Pensado para cron/systemd.