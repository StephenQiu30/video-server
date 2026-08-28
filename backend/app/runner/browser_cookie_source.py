"""Read browser Cookie jars without selecting an unrelated Chrome profile."""

from __future__ import annotations

import os
import sys
from http.cookiejar import CookieJar
from pathlib import Path
from typing import cast

from yt_dlp import YoutubeDL  # type: ignore[import-untyped]
from yt_dlp.utils import DownloadError  # type: ignore[import-untyped]


def load_browser_cookies(browser: str, profile: str | None) -> CookieJar:
    specification = (browser, profile, None, None)
    try:
        with YoutubeDL(
            {
                "cookiesfrombrowser": specification,
                "quiet": True,
                "no_warnings": True,
            }
        ) as ydl:
            return cast(CookieJar, ydl.cookiejar)
    except (DownloadError, OSError) as exc:
        raise OSError("browser session could not be read") from exc


def browser_profile_candidates(browser: str) -> tuple[Path, ...]:
    root = _chromium_profile_root(browser)
    if root is None or not root.is_dir():
        return ()
    profiles: dict[Path, int] = {}
    for directory in (root, *root.iterdir()):
        if not directory.is_dir() or directory.is_symlink():
            continue
        for cookie_database in (
            directory / "Network" / "Cookies",
            directory / "Cookies",
        ):
            try:
                modified = cookie_database.stat().st_mtime_ns
            except OSError:
                continue
            profiles[directory] = max(modified, profiles.get(directory, 0))
    return tuple(
        profile
        for profile, _modified in sorted(
            profiles.items(), key=lambda item: item[1], reverse=True
        )
    )


def _chromium_profile_root(browser: str) -> Path | None:
    if browser not in {"chrome", "chromium"}:
        return None
    if sys.platform == "darwin":
        relative = "Google/Chrome" if browser == "chrome" else "Chromium"
        return Path.home() / "Library/Application Support" / relative
    if sys.platform == "win32":
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data is None:
            return None
        relative = (
            "Google/Chrome/User Data" if browser == "chrome" else "Chromium/User Data"
        )
        return Path(local_app_data) / relative
    relative = "google-chrome" if browser == "chrome" else "chromium"
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / relative
