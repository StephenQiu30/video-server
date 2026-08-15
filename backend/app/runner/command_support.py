from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from app.runner.errors import RunnerFailure
from app.runner.process import ProcessSupervisor
from app.runner.settings import RunnerSettings


def default_supervisor(settings: RunnerSettings) -> ProcessSupervisor:
    return ProcessSupervisor(
        stdout_limit_bytes=settings.runner_output_capture_bytes,
        stderr_limit_bytes=settings.runner_output_capture_bytes,
        terminate_grace_seconds=settings.runner_terminate_grace_seconds,
    )


def child_environment(
    cwd: Path,
    proxy: str,
    *,
    browser_home: Path | None = None,
) -> dict[str, str]:
    return {
        "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
        "HOME": str(browser_home or cwd),
        "TMPDIR": str(cwd),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "HTTP_PROXY": proxy,
        "HTTPS_PROXY": proxy,
        "NO_PROXY": "",
        "http_proxy": proxy,
        "https_proxy": proxy,
        "no_proxy": "",
    }


def json_object(value: bytes, code: str) -> dict[str, Any]:
    try:
        decoded = json.loads(value)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RunnerFailure(code, status=502) from exc
    if not isinstance(decoded, dict):
        raise RunnerFailure(code, status=502)
    return decoded
