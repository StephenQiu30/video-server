from __future__ import annotations

import asyncio
import os
import shutil
from collections.abc import Callable
from pathlib import Path
from urllib.parse import urlsplit

from app.runner.settings import RunnerSettings


class RunnerReadiness:
    def __init__(
        self,
        settings: RunnerSettings,
        *,
        binary_exists: Callable[[str], str | None] = shutil.which,
    ) -> None:
        self._settings = settings
        self._binary_exists = binary_exists

    async def check(self) -> bool:
        binaries = (
            self._settings.runner_ytdlp_bin,
            self._settings.runner_ytdlp_js_runtime,
            self._settings.runner_ffmpeg_bin,
            self._settings.runner_ffprobe_bin,
        )
        if any(self._binary_exists(binary) is None for binary in binaries):
            return False
        workspace = self._settings.runner_workspace_root
        if not _writable_directory(workspace):
            return False
        endpoints = [self._settings.runner_egress_proxy]
        if self._settings.runner_youtube_pot_base_url is not None:
            endpoints.append(self._settings.runner_youtube_pot_base_url)
        return all(await asyncio.gather(*(_tcp_ready(url) for url in endpoints)))


def _writable_directory(path: Path) -> bool:
    return path.is_dir() and os.access(path, os.W_OK | os.X_OK)


async def _tcp_ready(url: str) -> bool:
    parsed = urlsplit(url)
    if parsed.hostname is None:
        return False
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        async with asyncio.timeout(2):
            _, writer = await asyncio.open_connection(parsed.hostname, port)
            writer.close()
            await writer.wait_closed()
    except (OSError, TimeoutError):
        return False
    return True
