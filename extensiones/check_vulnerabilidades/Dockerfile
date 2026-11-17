# extensiones-python:check_vulnerabilidades
# __version__ = "1.0.1"
FROM aquasec/trivy:0.76.1 AS trivy
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates \
 && apt-get upgrade -y \
 && rm -rf /var/lib/apt/lists/*

COPY --from=trivy /usr/local/bin/trivy /usr/local/bin/trivy
COPY utils/ ./utils/
COPY extensiones/check_vulnerabilidades/scanner.py .

RUN python scanner.py --self-check \
 && python -m pip uninstall -y pip \
 && rm -rf /root/.cache/pip

ENTRYPOINT ["python", "scanner.py"]
