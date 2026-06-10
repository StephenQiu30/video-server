"""Tests for scripts/check_local_services.sh dependency connectivity checks."""

import os
import subprocess

import pytest

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SCRIPT = os.path.join(ROOT_DIR, "scripts", "check_local_services.sh")


def _run_check(env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    """Run check_local_services.sh with optional env overrides."""
    merged = {**os.environ, "APP_ENV": "testing"}
    if env:
        merged.update(env)
    return subprocess.run(
        ["bash", SCRIPT],
        capture_output=True,
        text=True,
        timeout=15,
        env=merged,
        cwd=ROOT_DIR,
    )


class TestCheckLocalServices:
    """Verify that check_local_services.sh performs actual connectivity checks."""

    def test_script_has_syntax_check(self) -> None:
        """The script must pass bash syntax validation."""
        result = subprocess.run(["bash", "-n", SCRIPT], capture_output=True, text=True)
        assert result.returncode == 0, f"Syntax error: {result.stderr}"

    def test_script_exits_nonzero_when_postgres_unreachable(self) -> None:
        """Script must exit non-zero when PostgreSQL is unreachable."""
        result = _run_check(env={
            "DATABASE_URL": "postgresql+psycopg://video:video@127.0.0.1:19999/video_downloader",
        })
        assert result.returncode != 0, (
            "Expected non-zero exit when Postgres is unreachable, "
            f"got {result.returncode}. stdout={result.stdout}"
        )
        assert "PostgreSQL" in result.stdout
        assert "FAIL" in result.stdout or "不可达" in result.stdout or "无法连接" in result.stdout

    def test_script_exits_nonzero_when_redis_unreachable(self) -> None:
        """Script must exit non-zero when Redis is unreachable."""
        result = _run_check(env={
            "REDIS_URL": "redis://127.0.0.1:19998/0",
        })
        assert result.returncode != 0, (
            "Expected non-zero exit when Redis is unreachable, "
            f"got {result.returncode}. stdout={result.stdout}"
        )
        assert "Redis" in result.stdout

    def test_script_exits_nonzero_when_minio_unreachable(self) -> None:
        """Script must exit non-zero when MinIO is unreachable."""
        result = _run_check(env={
            "S3_ENDPOINT_URL": "http://127.0.0.1:19997",
        })
        assert result.returncode != 0, (
            "Expected non-zero exit when MinIO is unreachable, "
            f"got {result.returncode}. stdout={result.stdout}"
        )
        assert "MinIO" in result.stdout or "S3" in result.stdout

    def test_script_outputs_service_urls(self) -> None:
        """Script must display the configured service URLs."""
        result = _run_check(env={
            "DATABASE_URL": "postgresql+psycopg://test:test@127.0.0.1:19999/db",
            "REDIS_URL": "redis://127.0.0.1:19998/0",
            "S3_ENDPOINT_URL": "http://127.0.0.1:19997",
        })
        assert "127.0.0.1:19999" in result.stdout
        assert "127.0.0.1:19998" in result.stdout
        assert "127.0.0.1:19997" in result.stdout

    def test_script_provides_remediation_hints(self) -> None:
        """Script must suggest remediation when a service is unreachable."""
        result = _run_check(env={
            "DATABASE_URL": "postgresql+psycopg://video:video@127.0.0.1:19999/video_downloader",
        })
        # Should provide actionable hint for the failing service
        combined = result.stdout + result.stderr
        assert any(kw in combined for kw in [
            "提示", "hint", "建议", "suggestion", "启动", "start",
            "install", "安装", "docker", "brew",
        ]), f"No remediation hint found in output: {combined}"
