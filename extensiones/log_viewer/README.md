# Log Viewer

Visor web retro y de solo lectura para los logs generados por `utils/error_system.py`.
El encabezado permite alternar entre los temas `retro.css` (oscuro) y `classic.css` (claro original), sin JavaScript.

## Comportamiento

- Un proyecto corresponde al archivo activo `control.log` o `<prefijo>_control.log`; por ejemplo `alpha_control.log` aparece como `alpha`.
- Solo escanea la carpeta montada, no sus subcarpetas. Las rotaciones dentro de `historico/` no aparecen en la web.
- Lee todo el archivo activo, sin límite de antigüedad. Permite filtrar por proyecto, fechas, nivel y texto, y pagina los resultados.
- No modifica, mueve ni elimina ningún log.

La paginación carga las coincidencias del archivo activo en memoria. Si un archivo llega a ser muy grande, conviene reducir `LOG_ROTACION_DIAS` o cambiar el lector a lectura por bloques.

Al actualizar a `error_system` 2.4.0, detén primero los productores y mueve sus rotaciones antiguas fuera de la carpeta vigilada:

```bash
mkdir -p historico
for f in *.log.????-??-??; do [ -e "$f" ] && mv -n -- "$f" historico/; done
```

## Rotación del productor

`LOG_ROTACION_DIAS` ya controla cuándo se rota el archivo; ahora su valor predeterminado es 90 días. `LOG_BACKUPS` conserva 4 rotaciones por defecto, aproximadamente 360 días de histórico. Las rotaciones fechadas se guardan fuera de la carpeta vigilada, en `historico/` junto a `RUTA_CONTROL`; `LOG_HISTORICO_DIR` permite cambiar esa ubicación.

Configúralo en el entorno de **cada proyecto productor** si quieres otros valores:

```dotenv
LOG_ROTACION_DIAS=90
LOG_BACKUPS=4
# Opcional; por defecto se usa la carpeta historico junto a RUTA_CONTROL
# LOG_HISTORICO_DIR=/ruta/a/logs/historico
```

Para que el visor detecte cada proyecto por separado, usa un `LOG_PREFIJO` único en cada productor.

## Ejecutar sin Docker

En Ubuntu/Debian instala Python y el soporte para entornos virtuales:

```bash
sudo apt update
sudo apt install -y python3 python3-venv
```

Desde este directorio crea el entorno aislado e instala las dependencias:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m unittest discover -s . -v
```

Para iniciar la web con los logs de prueba:

```bash
export LOGS_DIR="$(realpath ../../pruebas/log_viewer)"
export ADMIN_USERNAME=admin
export ADMIN_PASSWORD='cambia-esto-por-una-frase-larga'
export SECRET_KEY="$(.venv/bin/python -c 'import secrets; print(secrets.token_urlsafe(48))')"
export COOKIE_SECURE=false
.venv/bin/python app.py
```

Abre `http://127.0.0.1:8080`. `COOKIE_SECURE=false` es solo para pruebas por HTTP local.

## Docker Compose

1. Si todavía no tienes `.env`, copia la plantilla sin sobrescribir configuraciones existentes: `cp -n .env.example .env`. Establece `LOGS_PATH` con la ruta absoluta a la carpeta de logs.
2. Define `ADMIN_USERNAME`, `ADMIN_PASSWORD` (mínimo 12 caracteres) y un `SECRET_KEY` aleatorio de al menos 32 caracteres. Puedes generarlo con `python3 -c 'import secrets; print(secrets.token_urlsafe(48))'`.
3. Para HTTPS deja `COOKIE_SECURE=true`. Con el puerto predeterminado, el servicio solo escucha en `127.0.0.1:8080`, para un proxy inverso en el host.
4. Desde este directorio ejecuta:

   ```bash
   docker compose up -d --build
   docker compose logs -f log-viewer
   ```

Si el proxy está en otro contenedor, elimina el bloque `ports` y conecta ambos servicios a una red Docker compartida. Detén el visor con `docker compose down`.

El contenedor corre como usuario no-root y monta los logs en solo lectura; ese usuario debe poder leer los archivos y atravesar la carpeta.

`.env` está ignorado por Git; no guardes credenciales en la imagen ni en el repositorio.
