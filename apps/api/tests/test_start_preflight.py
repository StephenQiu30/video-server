"""Tests for scripts/start.sh preflight dependency check integration."""

import os
import subprocess

import pytest

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
START_SCRIPT = os.path.join(ROOT_DIR, "scripts", "start.sh")


class TestStartPreflight:
    """Verify that start.sh runs dependency checks before starting."""

    def test_start_script_has_syntax_check(self) -> None:
        """The script must pass bash syntax validation."""
        result = subprocess.run(["bash", "-n", START_SCRIPT], capture_output=True, text=True)
        assert result.returncode == 0, f"Syntax error: {result.stderr}"

    def test_start_blocks_when_deps_unreachable(self) -> None:
        """start.sh must exit non-zero when dependencies are unreachable."""
        env = {
            **os.environ,
            "APP_ENV": "testing",
            "DATABASE_URL": "postgresql+psycopg://video:video@127.0.0.1:19999/video_downloader",
            "REDIS_URL": "redis://127.0.0.1:19998/0",
            "S3_ENDPOINT_URL": "http://127.0.0.1:19997",
            "API_PORT": "18765",
            "PYTHON_BIN": os.environ.get("PYTHON_BIN", "python3"),
        }
        result = subprocess.run(
            ["bash", START_SCRIPT, "local"],
            capture_output=True,
            text=True,
            timeout=15,
            env=env,
            cwd=ROOT_DIR,
        )
        assert result.returncode != 0, (
            f"Expected non-zero exit when deps unreachable, got {result.returncode}. "
            f"stdout={result.stdout[-500:]}"
        )
        combined = result.stdout + result.stderr
        assert "依赖" in combined or "不可达" in combined or "FAIL" in combined

    def test_start_respects_skip_preflight(self) -> None:
        """start.sh must skip preflight when SKIP_PREFLIGHT_CHECK=1."""
        env = {
            **os.environ,
            "APP_ENV": "testing",
            "SKIP_DB_BOOTSTRAP": "true",
            "DATABASE_URL": "postgresql+psycopg://video:video@127.0.0.1:19999/video_downloader",
            "REDIS_URL": "redis://127.0.0.1:19998/0",
            "S3_ENDPOINT_URL": "http://127.0.0.1:19997",
            "SKIP_PREFLIGHT_CHECK": "1",
            "API_PORT": "18765",
            "PYTHON_BIN": os.environ.get("PYTHON_BIN", "python3"),
        }
        # The script starts uvicorn which runs indefinitely.
        # A timeout is expected; we verify the preflight was skipped
        # by checking the partial output.
        try:
            result = subprocess.run(
                ["bash", START_SCRIPT, "local"],
                capture_output=True,
                text=True,
                timeout=10,
                env=env,
                cwd=ROOT_DIR,
            )
            combined = result.stdout + result.stderr
        except subprocess.TimeoutExpired as exc:
            out = exc.output if isinstance(exc.output, str) else (exc.output or b"").decode(errors="replace")
            err = exc.stderr if isinstance(exc.stderr, str) else (exc.stderr or b"").decode(errors="replace")
            combined = out + err

        assert "跳过依赖预检" in combined, (
            f"Expected '跳过依赖预检' in output. combined={combined[-300:]}"
        )
