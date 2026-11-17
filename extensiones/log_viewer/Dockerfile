# extensiones-python:log_viewer
# __version__ = "1.0.1"
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

RUN apt-get update \
 && apt-get upgrade -y \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
 && pip uninstall -y pip \
 && rm -rf /root/.cache/pip \
 && useradd --system --user-group --uid 10001 app
COPY --chown=app:app app.py log_reader.py ./
COPY --chown=app:app templates/ ./templates/
COPY --chown=app:app static/ ./static/
USER app
EXPOSE 8080
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "app:app"]
