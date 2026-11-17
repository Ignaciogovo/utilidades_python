# Extensiones

`utils/` contiene utilidades Python reutilizables; `extensiones/` contiene servicios y aplicaciones Docker que las complementan. Cada extensión documenta su configuración y despliegue en su propio directorio; algunas usan archivos de `utils/` al construir la imagen.

| Extensión | Versión | Qué hace | Documentación |
|---|---|---|---|
| `enviar_notificaciones/` | 1.0.1 | Despacha por correo los JSON generados por `utils/enviar_notificaciones.py`. | [doc.txt](enviar_notificaciones/doc.txt) |
| `log_viewer/` | 1.0.1 | Visor web de solo lectura para los logs de control. | [README.md](log_viewer/README.md) |
| `check_vulnerabilidades/` | 1.0.1 | Escanea imágenes Docker locales con Trivy y genera notificaciones compatibles con `error_system`. | [README.md](check_vulnerabilidades/README.md) |

Las extensiones pueden tener dependencias propias; no se instalan en `utils/`.

Cada extensión versiona su `Dockerfile` con la cabecera `# extensiones-python:nombre` + `# __version__` (bump en cualquier cambio que entre en la imagen). Referencia rápida para IAs en [GUIA_IA.md](GUIA_IA.md). Para saber si una copia en otro proyecto está desactualizada (una extensión o `extensiones/` entera):

```bash
python extensiones/check_updates.py <extensiones_origen> <extensiones_destino>
```
