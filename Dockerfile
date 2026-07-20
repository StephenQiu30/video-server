FROM python:3.12-slim-bookworm AS builder

ARG UV_VERSION=0.7.12
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=0 \
    SOURCE_DATE_EPOCH=0 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:/root/.local/bin:${PATH}"

WORKDIR /app

RUN pip install --no-cache-dir "uv==${UV_VERSION}"

COPY pyproject.toml uv.lock README.md LICENSE alembic.ini ./
COPY alembic ./alembic
RUN uv sync --frozen --no-dev --no-install-project \
    && find /app/.venv -name uv_cache.json -delete \
    && find /app/.venv -name RECORD -exec sed -i '/uv_cache.json/d' {} + \
    && find /app/.venv -exec touch -h -d '@0' {} + \
    && find /usr/local/lib/python3.12/site-packages/uv* -exec touch -h -d '@0' {} + \
    && find /tmp -maxdepth 1 -name 'uv-*.lock' -delete \
    && touch -h -d '@0' /root /tmp

COPY src ./src
RUN uv sync --frozen --no-dev \
    && find /app/.venv -name uv_cache.json -delete \
    && find /app/.venv -name RECORD -exec sed -i '/uv_cache.json/d' {} + \
    && find /app/.venv -exec touch -h -d '@0' {} + \
    && find /usr/local/lib/python3.12/site-packages/uv* -exec touch -h -d '@0' {} + \
    && find /tmp -maxdepth 1 -name 'uv-*.lock' -delete \
    && touch -h -d '@0' /root /tmp

FROM python:3.12-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:${PATH}" \
    XDG_CACHE_HOME=/tmp/.cache

WORKDIR /app

RUN apt-get update \
    && apt-get install --no-install-recommends -y ca-certificates ffmpeg \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 appuser \
    && mkdir -p /tmp/video-downloads /tmp/.cache \
    && chown -R appuser:appuser /app /tmp/video-downloads /tmp/.cache

COPY --from=builder --chown=appuser:appuser /app /app

USER appuser

EXPOSE 19090
CMD ["python", "-m", "src.main"]
