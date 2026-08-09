from __future__ import annotations

import json
import os
from pathlib import Path

from .config import CliAdapterConfig

_PROFILE = "video_analysis"
_KNOWN_TOOL_PREFIXES = (
    Path("/opt/homebrew"),
    Path("/home/linuxbrew/.linuxbrew"),
    Path("/usr/local"),
    Path("/opt/local"),
)


def codex_permission_arguments(config: CliAdapterConfig) -> tuple[str, ...]:
    filesystem = _filesystem_value(_media_tool_root(config))
    return (
        "-c",
        f'default_permissions="{_PROFILE}"',
        "-c",
        f"permissions.{_PROFILE}.filesystem={filesystem}",
        "-c",
        f"permissions.{_PROFILE}.network.enabled=false",
    )


def _filesystem_value(tool_root: Path) -> str:
    quoted_root = json.dumps(str(tool_root))
    return (
        '{":minimal"="read",'
        f'{quoted_root}="read",'
        '":workspace_roots"={"."="read",work="write",'
        'output="write",tmp="write"}}'
    )


def _media_tool_root(config: CliAdapterConfig) -> Path:
    media_paths = (config.ffmpeg.resolve(), config.ffprobe.resolve())
    for prefix in _KNOWN_TOOL_PREFIXES:
        if all(path.is_relative_to(prefix) for path in media_paths):
            return prefix
    common = Path(os.path.commonpath(media_paths))
    if common == Path(common.anchor) or common == Path.home():
        raise ValueError("ffmpeg and ffprobe must share a restricted tool root")
    return common if common.is_dir() else common.parent
