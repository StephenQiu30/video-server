from __future__ import annotations

import os
import shutil
from pathlib import Path

from .config import CliAdapterConfig


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
    environment = {
        "PATH": path,
        "HOME": str(Path.home()),
        "TMPDIR": str(workspace / "tmp"),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
    }
    codex_home = os.environ.get("CODEX_HOME")
    if codex_home:
        environment["CODEX_HOME"] = codex_home
    return environment
