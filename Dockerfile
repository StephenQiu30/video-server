FROM node:22-alpine AS frontend-builder

ARG NPM_VERSION=11.16.0
ENV SOURCE_DATE_EPOCH=0
WORKDIR /workspace/frontend

RUN npm install --global "npm@${NPM_VERSION}"
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim-bookworm AS backend-builder

ARG UV_VERSION=0.7.12
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=0 \
    UV_LINK_MODE=copy \
    PATH="/app/backend/.venv/bin:/root/.local/bin:${PATH}"
WORKDIR /app/backend

RUN pip install --no-cache-dir "uv==${UV_VERSION}"
COPY backend/pyproject.toml backend/uv.lock backend/README.md ./
RUN uv sync --frozen --no-dev --no-install-project
COPY backend/app ./app
RUN uv sync --frozen --no-dev

FROM python:3.12-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/backend/.venv/bin:${PATH}" \
    FRONTEND_DIST_DIR=/app/frontend/dist
WORKDIR /app/backend

RUN apt-get update \
    && apt-get install --no-install-recommends -y ca-certificates ffmpeg \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app

COPY --from=backend-builder --chown=appuser:appuser /app/backend /app/backend
COPY --from=frontend-builder --chown=appuser:appuser /workspace/frontend/dist /app/frontend/dist

USER appuser
EXPOSE 19090
CMD ["python", "-m", "app.main"]
