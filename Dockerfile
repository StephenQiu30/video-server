# ==========================================
# Phase 1: Python Base
# ==========================================
FROM python:3.12-slim AS python-base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/apps/api:/app/apps/worker:/app/packages/shared

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg ca-certificates fonts-wqy-microhei \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ==========================================
# Phase 2: App (API + Queue Consumer)
# ==========================================
FROM python-base AS app
COPY apps/api/requirements.txt /app/apps/api/requirements.txt
COPY apps/worker/requirements.txt /app/apps/worker/requirements.txt
RUN pip install --no-cache-dir -r /app/apps/api/requirements.txt \
    && pip install --no-cache-dir -r /app/apps/worker/requirements.txt
COPY apps/api /app/apps/api
COPY apps/worker /app/apps/worker
COPY packages /app/packages
EXPOSE 8000
CMD ["python", "-m", "app.runtime"]
