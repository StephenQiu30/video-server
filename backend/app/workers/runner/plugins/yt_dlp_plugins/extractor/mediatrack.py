from __future__ import annotations

import math
import re
from typing import Any

from yt_dlp.extractor.common import InfoExtractor  # type: ignore[import-untyped]
from yt_dlp.utils import ExtractorError  # type: ignore[import-untyped]

_API_ROOT = "https://kayn.api.mediatrack.cn"
_ANONYMOUS_MEMBER_ID = "-1"
_MEDIA_URL = re.compile(r"https://(?:[a-z0-9-]+\.)+mediatrack\.cn/")
_LONG_EDGE_LIMIT = {
    "FHD": 1920,
    "HD": 1280,
    "SD": 854,
    "LD": 640,
}
_QUALITY = {
    "ORIGINAL_RES": 4,
    "FHD": 3,
    "HD": 2,
    "SD": 1,
    "LD": 0,
}


class MediaTrackReviewIE(InfoExtractor):  # type: ignore[misc]
    _VALID_URL = (
        r"https?://app\.mediatrack\.cn/reviews/"
        r"(?P<review_id>[0-9]+)/(?P<asset_id>[0-9]+)(?:[/?#]|$)"
    )

    def _real_extract(self, url: str) -> dict[str, Any]:
        match = self._match_valid_url(url)
        review_id = match.group("review_id")
        asset_id = match.group("asset_id")
        common_query = {"org_member_id": _ANONYMOUS_MEMBER_ID}

        token_response = self._download_json(
            f"{_API_ROOT}/v1/public/links/{review_id}/token",
            review_id,
            note="Requesting MediaTrack public-link token",
            query={"password": "", **common_query},
        )
        token_data = _response_data(token_response, "public-link token")
        token = token_data.get("token")
        if not isinstance(token, str) or not token:
            raise ExtractorError(
                "MediaTrack public-link token is unavailable",
                expected=True,
            )

        asset_response = self._download_json(
            f"{_API_ROOT}/v1/public/links/{review_id}/assets/{asset_id}",
            asset_id,
            note="Downloading MediaTrack public asset metadata",
            query={"link_token": token, **common_query},
        )
        asset = _response_data(asset_response, "public asset")
        file_data = _mapping(asset.get("file"))
        mime = str(file_data.get("mime") or "")
        if not mime.startswith("video/"):
            raise ExtractorError(
                "MediaTrack asset is not a public video",
                expected=True,
            )

        width, height, fps = _source_video(file_data)
        duration = _positive_number(file_data.get("duration"))
        if duration is None:
            format_info = _mapping(_mapping(file_data.get("info")).get("Format"))
            duration = _positive_number(format_info.get("Duration"))

        formats: list[dict[str, Any]] = []
        transcodes = file_data.get("transcodes")
        if isinstance(transcodes, list):
            for raw in transcodes:
                transcode = _mapping(raw)
                label = str(transcode.get("res") or "").upper()
                media_url = transcode.get("file")
                if (
                    transcode.get("state") != "success"
                    or transcode.get("has_rights") is not True
                    or not isinstance(media_url, str)
                    or _MEDIA_URL.match(media_url) is None
                    or label not in _QUALITY
                ):
                    continue
                format_width, format_height = _scaled_dimensions(
                    width,
                    height,
                    _LONG_EDGE_LIMIT.get(label),
                )
                media_format: dict[str, Any] = {
                    "format_id": label.casefold(),
                    "format_note": label.replace("_", " "),
                    "url": media_url,
                    "manifest_url": media_url,
                    "protocol": "m3u8_native",
                    "ext": "mp4",
                    "width": format_width,
                    "height": format_height,
                    "fps": fps,
                    "vcodec": "h264",
                    "acodec": "aac",
                    "quality": _QUALITY.get(label, -1),
                }
                if label == "ORIGINAL_RES":
                    media_format["filesize_approx"] = _positive_int(
                        file_data.get("size") or asset.get("size")
                    )
                formats.append(media_format)

        if not formats:
            raise ExtractorError(
                "MediaTrack public video has no authorized playable formats",
                expected=True,
            )
        formats.sort(key=lambda item: int(item["quality"]), reverse=True)

        return {
            "id": asset_id,
            "display_id": str(file_data.get("id") or asset_id),
            "title": str(asset.get("title") or asset_id),
            "duration": duration,
            "formats": formats,
            "live_status": "not_live",
            "webpage_url": url,
        }


def _response_data(payload: object, resource: str) -> dict[str, Any]:
    response = _mapping(payload)
    data = response.get("data")
    if response.get("status") != "SUCCESS" or not isinstance(data, dict):
        raise ExtractorError(
            f"MediaTrack {resource} is unavailable",
            expected=True,
        )
    return data


def _mapping(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _source_video(
    file_data: dict[str, Any],
) -> tuple[int | None, int | None, float | None]:
    info = _mapping(file_data.get("info"))
    streams = _mapping(info.get("Streams"))
    video_list = _mapping(streams.get("VideoStreamList")).get("VideoStream")
    video = (
        _mapping(video_list[0]) if isinstance(video_list, list) and video_list else {}
    )
    return (
        _positive_int(video.get("Width")),
        _positive_int(video.get("Height")),
        _positive_number(video.get("Fps")),
    )


def _scaled_dimensions(
    width: int | None,
    height: int | None,
    long_edge_limit: int | None,
) -> tuple[int | None, int | None]:
    if width is None or height is None or long_edge_limit is None:
        return width, height
    long_edge = max(width, height)
    if long_edge <= long_edge_limit:
        return width, height
    scale = long_edge_limit / long_edge
    return _even(width * scale), _even(height * scale)


def _even(value: float) -> int:
    return max(2, round(value / 2) * 2)


def _positive_int(value: object) -> int | None:
    number = _positive_number(value)
    return int(number) if number is not None else None


def _positive_number(value: object) -> float | None:
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) and number > 0 else None
