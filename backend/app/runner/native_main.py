"""Run an operator Media Runner as a loopback-only host service."""

from __future__ import annotations

import os
from pathlib import Path

import uvicorn
from dotenv import dotenv_values

from app.runner.main import create_app
from app.runner.settings import RunnerSettings


def main() -> None:
    env_file = _env_file()
    native_values = dotenv_values(env_file) if env_file is not None else {}
    configured_host = native_values.get("NATIVE_RUNNER_HOST")
    host = (
        configured_host
        if isinstance(configured_host, str)
        else os.getenv("NATIVE_RUNNER_HOST", "127.0.0.1")
    )
    if host not in {"127.0.0.1", "::1"}:
        raise ValueError("Native Runner must bind to a loopback address")
    try:
        configured_port = native_values.get("NATIVE_RUNNER_PORT")
        port = int(
            configured_port
            if isinstance(configured_port, str)
            else os.getenv("NATIVE_RUNNER_PORT", "19101")
        )
    except ValueError as exc:
        raise ValueError("Native Runner port must be an integer") from exc
    if not 1024 <= port <= 65_535:
        raise ValueError("Native Runner port must be between 1024 and 65535")
    uvicorn.run(
        create_app(
            RunnerSettings(
                _env_file=env_file,
                _env_file_encoding="utf-8",
            )
            if env_file is not None
            else None
        ),
        host=host,
        port=port,
        access_log=False,
        server_header=False,
    )


def _env_file() -> Path | None:
    configured = os.getenv("NATIVE_RUNNER_ENV_FILE")
    if configured is None:
        return None
    configured_path = Path(configured).expanduser()
    if configured_path.is_symlink():
        raise ValueError("Native Runner env file must be a regular file")
    path = configured_path.resolve()
    if not path.is_file():
        raise ValueError("Native Runner env file must be a regular file")
    return path


if __name__ == "__main__":
    main()
