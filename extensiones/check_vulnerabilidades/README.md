# Check vulnerabilidades

Escanea las imágenes locales de Docker con Trivy y convierte las
vulnerabilidades encontradas en ficheros JSON compatibles con
`utils/error_system.py`. La extensión no actualiza ni elimina imágenes.

## Instalación

Copia la carpeta dentro de un proyecto que tenga también `utils/`, porque el
`Dockerfile` reutiliza `utils/error_system.py` y `utils/json_writer.py`:

```bash
cp -r extensiones/check_vulnerabilidades /opt/mi-proyecto/extensiones/
cp -r utils /opt/mi-proyecto/
cd /opt/mi-proyecto/extensiones/check_vulnerabilidades
cp .env.example .env
```

Edita `.env`. Lo mínimo es ajustar:

```dotenv
RUTA_NOTIFICACIONES_HOST=/srv/notificaciones
RUTA_LOGS_HOST=/srv/logs
RUTA_ESTADO_HOST=/srv/docker-vulnerabilidades
```

`CARPETA_ERRORES` y `RUTA_CONTROL` son las rutas que verá el contenedor.
`RUTA_NOTIFICACIONES_HOST` y `RUTA_LOGS_HOST` son las rutas equivalentes del
servidor. `RUTA_ESTADO_HOST` conserva el historial para no repetir correos.

## Uso

Construye y ejecuta el análisis:

```bash
docker compose build --pull
docker compose run --rm check-vulnerabilidades
```

Por defecto analiza solo las imágenes usadas por contenedores activos. Para
hacer un inventario completo de imágenes locales:

```dotenv
SOLO_EN_USO=0
```

Para limitarlo:

```dotenv
IMAGENES=ghcr.io/immich-app/immich-server:release,tailscale/tailscale:latest
```

También se aceptan patrones simples, por ejemplo `*immich*`.

Las imágenes se deduplican por `ImageID`, por lo que una misma imagen con
varias etiquetas solo se analiza una vez. Las imágenes sin etiqueta (`<none>`)
se excluyen; usa `INCLUIR_DANGLING=1` para incluirlas. `INCLUIR_DETENIDOS=1`
añade contenedores detenidos al modo `SOLO_EN_USO`.

## Notificaciones

Cada imagen con vulnerabilidades genera un único resumen con el total y el
desglose por severidad. Incluye también un comando `docker image rm <id>` para
limpiar una imagen antigua, pero no se ejecuta automáticamente. El estado
persistente evita repetir el correo mientras no cambien el `ImageID`, el CVE,
el paquete o la versión instalada. `registrar_errores()` crea el JSON en
`CARPETA_ERRORES`; después `enviar_notificaciones` puede enviarlo por correo.

No necesitas mantener un fichero de excepciones: las vulnerabilidades sin
parche se excluyen con `IGNORAR_SIN_CORREGIR=1` y el estado evita repetir las
ya notificadas. Para forzar avisos otra vez, elimina el fichero indicado por
`ESTADO_FILE`.

Sin vulnerabilidades no se crea ningún fichero de notificación.

Los códigos de salida son:

- `0`: sin vulnerabilidades en el criterio configurado.
- `1`: se encontraron vulnerabilidades.
- `2`: falló el acceso a Docker o el análisis.

## Self-check

```bash
cd /opt/mi-proyecto
docker build --pull -f extensiones/check_vulnerabilidades/Dockerfile \
  -t check-vulnerabilidades .
docker run --rm --entrypoint python check-vulnerabilidades scanner.py --self-check
```

## Seguridad

El socket `/var/run/docker.sock` permite controlar Docker y equivale
prácticamente a acceso de administrador del servidor. Ejecuta esta extensión
solo en un servidor de confianza y no expongas el socket por TCP.
