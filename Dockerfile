# ==========================================
# Phase 1: Python Base (API & Worker)
# ==========================================
FROM python:3.12-slim AS python-base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/apps/api:/app/apps/worker:/app/packages/shared

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ==========================================
# Phase 2: Python API
# ==========================================
FROM python-base AS api
COPY apps/api/requirements.txt /app/apps/api/requirements.txt
RUN pip install --no-cache-dir -r /app/apps/api/requirements.txt
COPY apps/api /app/apps/api
COPY packages /app/packages
# Copy built frontend from web-builder
COPY --from=web-builder /app/apps/web/dist /app/apps/api/static
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# ==========================================
# Phase 3: Python Worker
# ==========================================
FROM python-base AS worker
COPY apps/api/requirements.txt /app/apps/api/requirements.txt
COPY apps/worker/requirements.txt /app/apps/worker/requirements.txt
RUN pip install --no-cache-dir -r /app/apps/worker/requirements.txt
COPY apps/worker /app/apps/worker
COPY packages /app/packages
CMD ["python", "-m", "worker.main"]

# ==========================================
# Phase 4: Frontend Builder
# ==========================================
FROM node:20-alpine AS web-builder
WORKDIR /app
COPY apps/web/package*.json ./apps/web/
RUN cd apps/web && npm ci
COPY apps/web ./apps/web
RUN cd apps/web && npm run build

