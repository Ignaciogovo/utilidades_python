# extensiones-python:enviar_notificaciones
# __version__ = "1.0.1"
FROM python:3.11-slim
WORKDIR /app

RUN apt-get update \
 && apt-get upgrade -y \
 && rm -rf /var/lib/apt/lists/*

COPY utils/ ./utils/
RUN python -m utils.enviar_notificaciones \
 && pip uninstall -y pip
ENTRYPOINT ["python", "-m", "utils.enviar_notificaciones"]
