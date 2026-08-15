from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from app.runner.plugins.yt_dlp_plugins.extractor.tiktok_browser_session import (
    _TikTokBrowserSessionIE,
    _without_transport_impersonation,
)
from yt_dlp.extractor.tiktok import TikTokIE  # type: ignore[import-untyped]


def test_webpage_request_drops_transport_impersonation() -> None:
    original = {"note": "Downloading webpage", "impersonate": True}

    assert _without_transport_impersonation(original) == {"note": "Downloading webpage"}
    assert original["impersonate"] is True


def test_plugin_registers_as_the_builtin_tiktok_override() -> None:
    assert _TikTokBrowserSessionIE.IE_NAME == "TikTok+browser_session"
    assert issubclass(_TikTokBrowserSessionIE, TikTokIE)
    backend_root = Path(__file__).resolve().parents[3]
    result = subprocess.run(
        [
            str(Path(sys.executable).with_name("yt-dlp")),
            "--ignore-config",
            "--verbose",
            "--plugin-dirs",
            str(backend_root / "app/runner"),
            "--simulate",
            "--",
            "file:///disabled",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert "browser_session (TikTokIE)" in result.stderr
    assert str(backend_root / "app/runner/plugins/yt_dlp_plugins") in result.stderr
