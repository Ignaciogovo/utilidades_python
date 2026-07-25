FROM python:3.11-slim
WORKDIR /app
COPY utils/ ./utils/
RUN python -m utils.enviar_notificaciones
ENTRYPOINT ["python", "-m", "utils.enviar_notificaciones"]
