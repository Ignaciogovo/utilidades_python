# Guía para IAs — `extensiones/`

Referencia rápida de las extensiones de esta carpeta. Pensada para que una IA
las use en un proyecto que ya las tenga copiadas en su propio `extensiones/`
(o desplegadas por su cuenta).

A diferencia de `utils/` (ficheros `.py` que se copian uno a uno), una
extensión es una **carpeta completa**: una aplicación o servicio Docker
autocontenido que complementa a las utilidades.

## Convenciones

- Cada subcarpeta de `extensiones/` es una extensión independiente.
- Se copia **la carpeta entera** de la extensión (o `extensiones/` completa),
  no archivo a archivo.
- Puede tener dependencias propias (`requirements.txt`); nunca se instalan en
  `utils/`.
- **Toda extensión tiene un `Dockerfile`** con cabecera estándar:
  `# extensiones-python:nombre` + `# __version__ = "X.Y.Z"`. Bump de versión
  cuando cambie cualquier cosa que entre en la imagen (sus ficheros propios o
  los `utils/` que copie en el build). No quitar la cabecera.
- Configuración por env vars (`.env`); credenciales nunca en la imagen ni en
  el repo.
- Cada extensión documenta su despliegue en su propio directorio y tiene un
  self-check; córrelo antes de cerrar cualquier cambio en ella.

## Catálogo

| Extensión | Versión | Qué hace | Tipo |
|---|---|---|---|
| `enviar_notificaciones` | 1.0.0 | Contenedor one-shot que despacha por correo los JSON pendientes de `error_system` (envuelve `utils/enviar_notificaciones.py`) | one-shot (cron) |
| `log_viewer` | 1.0.0 | Visor web de solo lectura para los logs de control de `error_system` | servicio web |

## Despliegue mínimo por extensión

### `enviar_notificaciones`

Build con **contexto en la raíz del repo** (su Dockerfile hace `COPY utils/`,
así que necesita `utils/` junto a la carpeta de la extensión):

```bash
cd /ruta/al/repo
docker build -f extensiones/enviar_notificaciones/Dockerfile -t enviar-notificaciones .
```

Run one-shot (cron lo relanza cada N minutos):

```bash
docker run --rm --env-file .env -v $(pwd)/notificaciones:/app/notificaciones enviar-notificaciones
```

Self-check de la imagen (sin tocar nada):

```bash
docker run --rm --entrypoint python enviar-notificaciones -m utils.enviar_notificaciones
# → "enviar_notificaciones v1.1.0 OK"
```

Sin pendientes en `CARPETA_ERRORES` sale sin abrir SMTP. `RECEPTOR_CORREO`
no hace falta (el daemon lo setea solo). Las carpetas de errores, enviados y
logs se auto-crean.

### `log_viewer`

Autocontenida (build con contexto en su propia carpeta). Con Docker Compose:

```bash
cd extensiones/log_viewer
cp -n .env.example .env        # LOGS_PATH + credenciales
docker compose up -d --build
```

Sin Docker (tests + arranque local):

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m unittest discover -s .    # self-check
LOGS_DIR=/ruta/a/logs ADMIN_USERNAME=admin ADMIN_PASSWORD='frase-larga' \
  SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))') \
  COOKIE_SECURE=false .venv/bin/python app.py   # http://127.0.0.1:8080
```

Comportamiento: solo lee los archivos activos de la carpeta montada (no
subcarpetas, no `historico/`); un proyecto = un `control.log` o
`<prefijo>_control.log`; filtrado por proyecto/fechas/nivel/texto con
paginación; nunca modifica logs. Login con usuario/contraseña; `COOKIE_SECURE=false`
solo para HTTP local de pruebas.

## Relación con `utils/`

- `enviar_notificaciones` copia `utils/` dentro de la imagen en el build: si
  copias esta extensión a otro sitio, necesitas también `utils/` al lado para
  construir (y esa copia se chequea con `utils/check_updates.py`).
- `log_viewer` es autocontenida, pero **lee el formato de log de
  `error_system` 2.4.0**: un fichero activo por proyecto, rotaciones fechadas
  en `historico/` fuera del escaneo. Un `LOG_PREFIJO` único por productor se
  ve como un proyecto distinto en el visor.

## Mantener copias actualizadas

```bash
# todas las extensiones
python extensiones/check_updates.py <ruta/extensiones/origen> <ruta/extensiones/destino>

# una sola (carpetas concretas de la extensión en ambos lados)
python extensiones/check_updates.py extensiones/log_viewer/ <ruta/destino>/log_viewer/
```

Estados y exit codes iguales que `utils/check_updates.py`: `OK` /
`DESACTUALIZADO` / `MAS_NUEVO_EN_DESTINO` / `FALTA_EN_DESTINO` /
`SIN_VERSION`; `0` todo OK, `1` hay problemas, `2` error de args/rutas o
modos mezclados (un lado extensión y otro carpeta `extensiones/`). Sin
argumentos corre el self-check.

## Env vars

| Variable | Usada por | Default | Notas |
|---|---|---|---|
| `EMISOR_CORREO` | `enviar_notificaciones` | — | Remitente SMTP (obligatorio) |
| `PASS_CORREO` | `enviar_notificaciones` | — | App password (obligatorio) |
| `SMTP_HOST` / `SMTP_PORT` | `enviar_notificaciones` | `smtp.gmail.com` / `587` | STARTTLS |
| `EMAIL_GENERICO` | `enviar_notificaciones` | — | `To` por defecto si el error no trae `to_email` |
| `CARPETA_ERRORES` | `enviar_notificaciones` | `./notificaciones/` | JSON pendientes (montar en volumen) |
| `ENVIADOS_DIR` | `enviar_notificaciones` | `<CARPETA_ERRORES>/enviados` | Destino tras procesar un JSON |
| `RETENCION_HORAS` | `enviar_notificaciones` | `24` | Horas en `enviados/` antes de borrar |
| `PROYECTO` | `enviar_notificaciones` | `desconocido` | Campo `origen` en trazas |
| `RUTA_CONTROL` | `enviar_notificaciones` | `./logs/control.log` | Log de control dentro del contenedor |
| `LOGS_PATH` | `log_viewer` (compose) | — | Ruta **absoluta** del host a la carpeta de logs; se monta `:ro` en `/logs` |
| `LOGS_DIR` | `log_viewer` | `/logs` | Carpeta de logs que lee la app (ya apuntada por compose) |
| `LOG_VIEWER_BIND` / `LOG_VIEWER_PORT` | `log_viewer` (compose) | `127.0.0.1` / `8080` | Bind del puerto publicado |
| `ADMIN_USERNAME` | `log_viewer` | — | Usuario del login (obligatorio) |
| `ADMIN_PASSWORD` | `log_viewer` | — | Mínimo 12 caracteres (obligatorio) |
| `SECRET_KEY` | `log_viewer` | — | Mínimo 32 caracteres; genera con `secrets.token_urlsafe(48)` |
| `COOKIE_SECURE` | `log_viewer` | `true` | `false` solo para pruebas por HTTP local |

## Reglas de oro

- **Copia la carpeta de la extensión entera**, no ficheros sueltos.
- **`.env` nunca se commitea** ni entra en la imagen.
- **Los logs se montan en solo lectura** (`:ro`).
- **Las dependencias de una extensión no se instalan en `utils/`.**
- **Bump del `# __version__` del Dockerfile** en cualquier cambio que entre
  en la imagen; `check_updates` lo lee.
- **Self-check antes de cerrar** un cambio en una extensión.

Esta guía es autocontenida: asume que solo tienes esta carpeta
(`extensiones/`) y las extensiones que lista el catálogo. Para detalle de
despliegue mira el `doc.txt` / `README.md` de cada extensión.
