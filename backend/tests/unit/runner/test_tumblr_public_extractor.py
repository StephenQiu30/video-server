from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from app.runner.plugins.yt_dlp_plugins.extractor.tumblr_public import (
    _TumblrPublicPageIE,
)
from yt_dlp import YoutubeDL
from yt_dlp.extractor.tumblr import TumblrIE

URL = (
    "https://www.tumblr.com/maskofthedragon/626907179849564160/mona-talking-in-english"
)


def test_prefers_current_public_post_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    extractor = _TumblrPublicPageIE(YoutubeDL({"quiet": True, "no_warnings": True}))
    requests: list[tuple[str, str, dict[str, object]]] = []
    webpage = """
        <meta content="Mona talking in English" property="og:title"/>
        <meta content="Public post" property="og:description"/>
        <meta content="https://va.media.tumblr.com/video_720.mp4" property="og:video"/>
        <meta content="1920" property="og:video:width"/>
        <meta content="1080" property="og:video:height"/>
        <meta content="https://64.media.tumblr.com/cover.jpg" property="og:image"/>
    """

    def download_webpage(
        url: str,
        video_id: str,
        **kwargs: object,
    ) -> str:
        requests.append((url, video_id, kwargs))
        return webpage

    monkeypatch.setattr(extractor, "_download_webpage", download_webpage)

    info = extractor._real_extract(URL)

    assert info["id"] == "626907179849564160"
    assert info["title"] == "Mona talking in English"
    assert info["uploader_id"] == "maskofthedragon"
    assert info["formats"] == [
        {
            "url": "https://va.media.tumblr.com/video_720.mp4",
            "ext": "mp4",
            "width": 1920,
            "height": 1080,
        }
    ]
    assert info["thumbnail"] == "https://64.media.tumblr.com/cover.jpg"
    assert requests[0][0] == URL
    assert requests[0][1] == "626907179849564160"
    assert requests[0][2]["fatal"] is False


def test_plugin_registers_as_the_builtin_tumblr_override() -> None:
    assert _TumblrPublicPageIE.IE_NAME == "Tumblr+public_page"
    assert issubclass(_TumblrPublicPageIE, TumblrIE)
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

    assert "public_page (TumblrIE)" in result.stderr
    assert str(backend_root / "app/runner/plugins/yt_dlp_plugins") in result.stderr
