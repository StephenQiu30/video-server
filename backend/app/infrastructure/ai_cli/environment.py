from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path

from .config import CliAdapterConfig

_log = logging.getLogger(__name__)

_WINDOWS_RUNTIME_VARIABLES = ("SYSTEMROOT", "WINDIR", "COMSPEC", "PATHEXT")


def minimum_host_environment(path: str) -> dict[str, str]:
    environment = {
        "PATH": path,
        "HOME": str(Path.home()),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
    }
    if os.name == "nt":
        for name in _WINDOWS_RUNTIME_VARIABLES:
            value = os.environ.get(name)
            if value:
                environment[name] = value
    codex_home = os.environ.get("CODEX_HOME")
    if codex_home:
        environment["CODEX_HOME"] = codex_home
    return environment


def child_environment(config: CliAdapterConfig, workspace: Path) -> dict[str, str]:
    node = shutil.which("node")
    directories = [
        config.binary.parent,
        config.ffmpeg.parent,
        config.ffprobe.parent,
        Path("/usr/bin"),
        Path("/bin"),
    ]
    if node is not None:
        directories.insert(1, Path(node).resolve().parent)
    path = os.pathsep.join(dict.fromkeys(str(item) for item in directories))
    _log.debug(
        "child environment PATH: %s; ffmpeg=%s; ffprobe=%s",
        path,
        config.ffmpeg,
        config.ffprobe,
    )
    environment = minimum_host_environment(path)
    temporary = str(workspace / "tmp")
    environment["TMPDIR"] = temporary
    if os.name == "nt":
        environment["TEMP"] = temporary
        environment["TMP"] = temporary
    environment.update(config.extra_environment)
    return environment
