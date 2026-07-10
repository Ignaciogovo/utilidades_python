# Imagen base
FROM python:3.11-slim

# Crear directorio de trabajo
WORKDIR /app

# Copiar utilidad (ruta relativa al contexto de build, que debe ser la raíz del repo)
COPY ../utils/enviar_correo.py .

# Instalar dependencias (solo estándar, ya que usamos librerías estándar)
#RUN pip install --no-cache-dir

# Configurar entrypoint
ENTRYPOINT ["python", "enviar_correo.py"]
