from __future__ import annotations

import json
import sys
from pathlib import Path

from .config import CliAdapterConfig

_SERVER = "video_observer"
_TOOLS = ["probe_video", "inspect_video_overview", "inspect_video_frame"]


def video_observer_arguments(
    config: CliAdapterConfig,
    *,
    root: Path,
    duration_ms: int,
) -> tuple[str, ...]:
    backend = Path(__file__).resolve(strict=True).parents[3]
    arguments = [
        "-m",
        "app.infrastructure.ai_cli.media_mcp_server",
        "--workspace",
        str(root),
        "--ffmpeg",
        str(config.ffmpeg),
        "--ffprobe",
        str(config.ffprobe),
        "--duration-ms",
        str(duration_ms),
        "--maximum-images",
        str(config.max_frames),
        "--maximum-image-bytes",
        str(config.max_image_bytes),
    ]
    values = {
        f"mcp_servers.{_SERVER}.command": str(Path(sys.executable).resolve()),
        f"mcp_servers.{_SERVER}.args": arguments,
        f"mcp_servers.{_SERVER}.cwd": str(backend),
        f"mcp_servers.{_SERVER}.required": True,
        f"mcp_servers.{_SERVER}.enabled_tools": _TOOLS,
        f"mcp_servers.{_SERVER}.default_tools_approval_mode": "auto",
        f"mcp_servers.{_SERVER}.startup_timeout_sec": 10,
        f"mcp_servers.{_SERVER}.tool_timeout_sec": 90,
    }
    return tuple(
        item
        for key, value in values.items()
        for item in ("-c", f"{key}={json.dumps(value)}")
    )
