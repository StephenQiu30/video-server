from __future__ import annotations

from typing import Any

import pytest
from app.runner.plugins.yt_dlp_plugins.extractor.mediatrack import (
    MediaTrackReviewIE,
)
from yt_dlp.utils import ExtractorError

URL = (
    "https://app.mediatrack.cn/reviews/1234567890123456789/"
    "9876543210987654321?fileId=1111111111111111111&inviteid=public&type=0"
)


def asset_response(*, has_rights: bool = True) -> dict[str, Any]:
    return {
        "status": "SUCCESS",
        "data": {
            "id": "9876543210987654321",
            "title": "fixture.mp4",
            "size": "306617684",
            "file": {
                "id": "2222222222222222222",
                "mime": "video/mp4",
                "size": "306617684",
                "duration": 198,
                "info": {
                    "Streams": {
                        "VideoStreamList": {
                            "VideoStream": [
                                {"Width": "1080", "Height": "1920", "Fps": "29.97"}
                            ]
                        }
                    }
                },
                "transcodes": [
                    {
                        "res": "ORIGINAL_RES",
                        "file": "https://evelynn.api.mediatrack.cn/original.m3u8",
                        "state": "success",
                        "has_rights": has_rights,
                    },
                    {
                        "res": "HD",
                        "file": "https://evelynn.api.mediatrack.cn/hd.m3u8",
                        "state": "success",
                        "has_rights": has_rights,
                    },
                ],
            },
        },
    }


def test_extracts_authorized_public_hls_formats(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    extractor = MediaTrackReviewIE()
    calls: list[tuple[str, dict[str, object]]] = []
    responses = iter(
        [
            {"status": "SUCCESS", "data": {"token": "short-lived"}},
            asset_response(),
        ]
    )

    def download_json(
        url: str,
        video_id: str,
        *,
        query: dict[str, object],
        **kwargs: object,
    ) -> dict[str, Any]:
        calls.append((url, query))
        return next(responses)

    monkeypatch.setattr(extractor, "_download_json", download_json)

    info = extractor._real_extract(URL)

    assert info["id"] == "9876543210987654321"
    assert info["title"] == "fixture.mp4"
    assert info["duration"] == 198
    formats = info["formats"]
    assert isinstance(formats, list)
    assert [item["format_id"] for item in formats] == ["original_res", "hd"]
    assert (formats[0]["width"], formats[0]["height"]) == (1080, 1920)
    assert (formats[1]["width"], formats[1]["height"]) == (720, 1280)
    assert all(item["protocol"] == "m3u8_native" for item in formats)
    assert calls[0][1] == {"password": "", "org_member_id": "-1"}
    assert calls[1][1] == {
        "link_token": "short-lived",
        "org_member_id": "-1",
    }


def test_rejects_video_without_authorized_playable_format(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    extractor = MediaTrackReviewIE()
    responses = iter(
        [
            {"status": "SUCCESS", "data": {"token": "short-lived"}},
            asset_response(has_rights=False),
        ]
    )
    monkeypatch.setattr(
        extractor,
        "_download_json",
        lambda *args, **kwargs: next(responses),
    )

    with pytest.raises(ExtractorError, match="no authorized playable formats"):
        extractor._real_extract(URL)


def test_rejects_media_url_outside_mediatrack(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    extractor = MediaTrackReviewIE()
    response = asset_response()
    transcodes = response["data"]["file"]["transcodes"]
    for transcode in transcodes:
        transcode["file"] = "https://media.example/untrusted.m3u8"
    responses = iter(
        [
            {"status": "SUCCESS", "data": {"token": "short-lived"}},
            response,
        ]
    )
    monkeypatch.setattr(
        extractor,
        "_download_json",
        lambda *args, **kwargs: next(responses),
    )

    with pytest.raises(ExtractorError, match="no authorized playable formats"):
        extractor._real_extract(URL)


def test_only_matches_mediatrack_review_asset_urls() -> None:
    assert MediaTrackReviewIE.suitable(URL)
    assert not MediaTrackReviewIE.suitable("https://app.mediatrack.cn/reviews/123")
    assert not MediaTrackReviewIE.suitable("https://example.com/reviews/123/456")
