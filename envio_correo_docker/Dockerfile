# Imagen base
FROM python:3.11-slim

# Crear directorio de trabajo
WORKDIR /app

# Copiar script
COPY enviar_correo.py .

# Instalar dependencias (solo estándar, ya que usamos librerías estándar)
RUN pip install --no-cache-dir

# Configurar entrypoint
ENTRYPOINT ["python", "enviar_correo.py"]
