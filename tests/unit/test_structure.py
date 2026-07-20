from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).parents[2]


def test_source_is_directly_under_src_without_wrapper_package() -> None:
    assert (ROOT / "src" / "main.py").is_file()
    assert (ROOT / "src" / "core" / "config.py").is_file()
    assert not (ROOT / "src" / "video_server").exists()


def test_forbidden_optional_infrastructure_is_not_declared() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

    for forbidden in ("celery", "redis", "cobalt", "metube"):
        assert forbidden not in pyproject.lower()


def test_compose_files_cover_default_prod_and_infrastructure_modes() -> None:
    default = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    production = (ROOT / "docker-compose-prod.yml").read_text(encoding="utf-8")
    infrastructure = (ROOT / "docker-compose-env.yml").read_text(encoding="utf-8")

    assert not (ROOT / "compose.yml").exists()
    assert "alembic upgrade head && exec python -m src.main" in default
    assert "condition: service_healthy" in default
    assert "pull_policy: always" in production
    assert "api:" not in infrastructure
    assert "worker-download:" not in infrastructure
    assert "${MINIO_API_BIND:-127.0.0.1}" in infrastructure
    assert "${MINIO_CONSOLE_BIND:-127.0.0.1}" in infrastructure


def test_container_build_sets_reproducible_python_timestamp_source() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "FROM python:3.12-slim-bookworm AS builder" in dockerfile
    assert "FROM python:3.12-slim-bookworm AS runtime" in dockerfile
    assert "COPY --from=builder --chown=appuser:appuser /app /app" in dockerfile
    assert "SOURCE_DATE_EPOCH=0" in dockerfile
    assert "UV_COMPILE_BYTECODE=0" in dockerfile
    assert "find /app/.venv -name uv_cache.json -delete" in dockerfile
    assert (
        "find /app/.venv -name RECORD -exec sed -i '/uv_cache.json/d' {} +"
        in dockerfile
    )
    assert "find /app/.venv -exec touch -h -d '@0' {} +" in dockerfile
    assert (
        "find /usr/local/lib/python3.12/site-packages/uv* -exec touch -h -d '@0' {} +"
        in dockerfile
    )
    assert "find /tmp -maxdepth 1 -name 'uv-*.lock' -delete" in dockerfile
    assert "touch -h -d '@0' /root /tmp" in dockerfile

    runtime = dockerfile.split("FROM python:3.12-slim-bookworm AS runtime", 1)[1]
    assert "pip install" not in runtime
    assert 'CMD ["python", "-m", "src.main"]' in runtime
    assert "USER appuser" in runtime
