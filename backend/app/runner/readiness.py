from __future__ import annotations

import asyncio
import json
import os
import shutil
from collections.abc import Callable
from importlib.metadata import PackageNotFoundError, distribution
from pathlib import Path
from urllib.parse import urlsplit

from app.runner.settings import RunnerSettings
from app.runner.version import YTDLP_ENGINE_VERSION


class RunnerReadiness:
    def __init__(
        self,
        settings: RunnerSettings,
        *,
        binary_exists: Callable[[str], str | None] = shutil.which,
        session_ready: Callable[[], bool] = lambda: True,
    ) -> None:
        self._settings = settings
        self._binary_exists = binary_exists
        self._session_ready = session_ready

    async def check(self) -> bool:
        binaries = (
            self._settings.runner_ytdlp_bin,
            self._settings.runner_ytdlp_js_runtime,
            self._settings.runner_ffmpeg_bin,
            self._settings.runner_ffprobe_bin,
        )
        if any(self._binary_exists(binary) is None for binary in binaries):
            return False
        if not _runtime_packages_ready(self._settings):
            return False
        if not self._session_ready():
            return False
        workspace = self._settings.runner_workspace_root
        if not _writable_directory(workspace):
            return False
        egress_ready = await _tcp_ready(self._settings.runner_egress_proxy)
        if not egress_ready:
            return False
        return True


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


def _runtime_packages_ready(settings: RunnerSettings) -> bool:
    yt_dlp = _package_record("yt-dlp")
    pot_plugin = _package_record("bgutil-ytdlp-pot-provider")
    pot_release = _pot_release(settings.runner_youtube_pot_provider_version)
    expected_source = (
        "https://github.com/yt-dlp/yt-dlp/archive/"
        f"{settings.runner_ytdlp_commit}.tar.gz"
    )
    return bool(
        yt_dlp == (YTDLP_ENGINE_VERSION, expected_source)
        and pot_release is not None
        and pot_plugin is not None
        and pot_plugin[0] == pot_release
    )


def _package_record(name: str) -> tuple[str, str | None] | None:
    try:
        package = distribution(name)
    except PackageNotFoundError:
        return None
    raw_direct_url = package.read_text("direct_url.json")
    if raw_direct_url is None:
        return package.version, None
    try:
        direct_url = json.loads(raw_direct_url).get("url")
    except (json.JSONDecodeError, AttributeError):
        return package.version, None
    return package.version, direct_url if isinstance(direct_url, str) else None


def _pot_release(attestation_version: str) -> str | None:
    prefix = "bgutil-http-"
    if not attestation_version.startswith(prefix):
        return None
    release = attestation_version.removeprefix(prefix)
    return release or None
