FROM python:3.12-slim-bookworm

ARG UV_VERSION=0.7.12
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:/root/.local/bin:${PATH}"

WORKDIR /app

RUN apt-get update \
    && apt-get install --no-install-recommends -y ca-certificates ffmpeg \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir "uv==${UV_VERSION}"

COPY pyproject.toml uv.lock README.md LICENSE alembic.ini ./
COPY alembic ./alembic
RUN uv sync --frozen --no-dev --no-install-project

COPY src ./src
RUN uv sync --frozen --no-dev

RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /tmp/video-downloads \
    && chown -R appuser:appuser /app /tmp/video-downloads
USER appuser

EXPOSE 19090
CMD ["uv", "run", "--no-dev", "python", "-m", "src.main"]
