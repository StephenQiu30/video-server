# syntax=docker/dockerfile:1.7

FROM node:24-alpine AS frontend-builder

ARG NPM_VERSION=11.19.0
ENV SOURCE_DATE_EPOCH=0
WORKDIR /workspace/frontend

RUN --mount=type=cache,target=/root/.npm \
    npm install --global "npm@${NPM_VERSION}"
COPY --link frontend/package.json frontend/package-lock.json ./
RUN --mount=type=cache,target=/root/.npm \
    npm ci --ignore-scripts
COPY --link frontend/ ./
RUN npm rebuild \
    && npm run build

FROM node:24-bookworm-slim AS node-runtime

FROM python:3.12-slim-bookworm AS backend-builder

ARG UV_VERSION=0.11.32
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=0 \
    UV_LINK_MODE=copy \
    PATH="/app/backend/.venv/bin:/root/.local/bin:${PATH}"
WORKDIR /app/backend

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install "uv==${UV_VERSION}"
COPY --link backend/pyproject.toml backend/uv.lock backend/README.md ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project
COPY --link backend/app ./app
COPY --link backend/supply-chain/ ./supply-chain/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

FROM python:3.12-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/backend/.venv/bin:${PATH}" \
    FRONTEND_DIST_DIR=/app/frontend/out
WORKDIR /app/backend

RUN apt-get update \
    && apt-get install --no-install-recommends -y ca-certificates ffmpeg libstdc++6 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app

COPY --link --from=backend-builder --chown=10001:10001 /app/backend /app/backend
COPY --link --from=frontend-builder --chown=10001:10001 /workspace/frontend/out /app/frontend/out
COPY --link --from=node-runtime /usr/local/bin/node /usr/local/bin/node

USER appuser
EXPOSE 8101
CMD ["python", "-m", "app.main"]
