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
COPY apps/api/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY apps/api /app/apps/api
COPY packages /app/packages
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# ==========================================
# Phase 3: Python Worker
# ==========================================
FROM python-base AS worker
COPY apps/worker/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
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
# Build web (assuming Vite)
RUN cd apps/web && npm run build

# ==========================================
# Phase 5: Frontend Server (Nginx)
# ==========================================
FROM nginx:1.27-alpine AS web
COPY --from=web-builder /app/apps/web/dist /usr/share/nginx/html
RUN printf 'server { \
    listen 80; \
    server_name _; \
    root /usr/share/nginx/html; \
    index index.html; \
    location / { try_files $uri $uri/ /index.html; } \
    location = /health { access_log off; add_header Content-Type text/plain; return 200 "ok\\n"; } \
}' > /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
