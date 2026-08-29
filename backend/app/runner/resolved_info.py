"""Private persistence for one operation's fresh yt-dlp resolution."""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from pathlib import Path

from app.runner.errors import RunnerFailure


def write_resolved_info(path: Path, payload: Mapping[str, object]) -> None:
    try:
        data = json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode()
    except (TypeError, ValueError) as exc:
        raise RunnerFailure("invalid_inspection_response", status=502) from exc
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags, 0o600)
        with os.fdopen(descriptor, "wb", closefd=True) as output:
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
    except OSError as exc:
        raise RunnerFailure("runner_dependency_unavailable", status=503) from exc
