# Extensiones

`utils/` contiene utilidades Python reutilizables; `extensiones/` contiene servicios y aplicaciones Docker que las complementan. Cada extensión documenta su configuración y despliegue en su propio directorio; algunas usan archivos de `utils/` al construir la imagen.

| Extensión | Qué hace | Documentación |
|---|---|---|
| `enviar_notificaciones/` | Despacha por correo los JSON generados por `utils/enviar_notificaciones.py`. | [doc.txt](enviar_notificaciones/doc.txt) |
| `log_viewer/` | Visor web de solo lectura para los logs de control. | [README.md](log_viewer/README.md) |

Las extensiones pueden tener dependencias propias; no se instalan en `utils/`.
