# syntax=docker/dockerfile:1.7

# --- Egress Proxy Target (Stripe Smokescreen) ---
FROM golang:1.24-alpine AS egress-proxy-builder

WORKDIR /src
RUN CGO_ENABLED=0 go install -ldflags="-s -w" github.com/stripe/smokescreen@latest

FROM alpine:3.21 AS egress-proxy

RUN apk add --no-cache ca-certificates

COPY --from=egress-proxy-builder /go/bin/smokescreen /usr/local/bin/smokescreen

EXPOSE 3128

ENTRYPOINT ["smokescreen"]
CMD ["--listen-ip=0.0.0.0", "--listen-port=3128"]

# --- Backend Application Targets ---
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
COPY --link pyproject.toml uv.lock README.md ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project
COPY --link app ./app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

FROM python:3.12-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/backend/.venv/bin:${PATH}"
WORKDIR /app/backend

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    rm -f /etc/apt/apt.conf.d/docker-clean \
    && apt-get -o Acquire::Retries=5 update \
    && apt-get -o Acquire::Retries=5 install --no-install-recommends -y \
        ca-certificates ffmpeg libstdc++6 \
    && useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app

COPY --link --from=backend-builder --chown=10001:10001 /app/backend /app/backend
COPY --link --from=node-runtime /usr/local/bin/node /usr/local/bin/node

USER appuser
EXPOSE 8111
CMD ["python", "-m", "app.main"]
