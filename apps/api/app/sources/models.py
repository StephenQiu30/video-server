from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Literal
from urllib.parse import urlparse

from app.core.errors import AppError, ErrorCode
from app.schemas import ParseResponse, VideoFormat


class SourceCapability(StrEnum):
    HAS_VIDEO = "has_video"
    HAS_AUDIO = "has_audio"
    HAS_SUBTITLES = "has_subtitles"
    MULTI_RESOLUTION = "multi_resolution"


@dataclass(frozen=True)
class SourceRequest:
    url: str
    normalized_url: str
    hostname: str
    format_id: str | None = None

    @classmethod
    def from_url(cls, url: str, format_id: str | None = None) -> SourceRequest:
        hostname = (urlparse(url).hostname or "").lower()
        if not hostname:
            raise AppError(ErrorCode.INVALID_URL, "请输入有效的视频链接", 422)
        return cls(url=url, normalized_url=url, hostname=hostname, format_id=format_id)


@dataclass(frozen=True)
class MediaVariant:
    format_id: str
    ext: str | None = None
    resolution: str | None = None
    height: int | None = None
    width: int | None = None
    filesize: int | None = None
    vcodec: str | None = None
    acodec: str | None = None
    stream_type: Literal["video+audio", "video-only", "audio-only"] | None = None

    def __post_init__(self) -> None:
        if self.stream_type is None:
            st = _derive_stream_type(self.vcodec, self.acodec)
            object.__setattr__(self, "stream_type", st)


@dataclass(frozen=True)
class SubtitleTrack:
    language: str
    ext: str | None = None
    url: str | None = None


@dataclass(frozen=True)
class SourceInfo:
    title: str | None = None
    cover_url: str | None = None
    duration_seconds: int | None = None
    extractor: str | None = None
    variants: list[MediaVariant] = field(default_factory=list)
    subtitles: list[SubtitleTrack] = field(default_factory=list)
    capabilities: set[SourceCapability] = field(default_factory=set)
    raw_info: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SourceContext:
    request: SourceRequest
    platform_profile: Any | None = None
    adapter_name: str = ""


def _derive_stream_type(
    vcodec: str | None, acodec: str | None
) -> Literal["video+audio", "video-only", "audio-only"] | None:
    if vcodec == "none":
        return "audio-only"
    if acodec == "none":
        return "video-only"
    if vcodec is not None or acodec is not None:
        return "video+audio"
    return None


# --- SourceInfo → ParseResponse conversion ---

RECOMMENDED_FORMAT_ID = "bestvideo+bestaudio/best"
RESOLUTION_PRESETS = [
    (1080, "最高 1080p"),
    (720, "最高 720p"),
    (480, "最高 480p"),
    (360, "最高 360p"),
]

_WATERMARK_FREE_EXTRACTORS = {"BiliBili", "YouTube", "Vimeo", "Dailymotion"}
_WATERMARK_PLATFORM_EXTRACTORS = {"Douyin", "Kuaishou", "TikTok"}

SOURCE_SITE_NAMES = {
    "bilibili": "B 站",
    "douyin": "抖音",
    "kuaishou": "快手",
    "tiktok": "TikTok",
    "xiaohongshu": "小红书",
    "ixigua": "西瓜视频",
    "youtube": "YouTube",
    "vimeo": "Vimeo",
    "dailymotion": "Dailymotion",
    "weibo": "微博",
    "x": "X",
    "instagram": "Instagram",
}


def source_info_to_parse_response(
    url: str,
    info: SourceInfo,
    platform_profile: Any | None,
) -> ParseResponse:
    extractor = info.extractor
    format_watermark_hint = _derive_format_watermark_hint(extractor)
    raw_formats: list[VideoFormat] = []
    available_heights: set[int] = set()

    for variant in info.variants:
        if variant.height and variant.stream_type != "audio-only":
            available_heights.add(variant.height)

        resolution = variant.resolution
        if not resolution and variant.width and variant.height:
            resolution = f"{variant.width}x{variant.height}"

        label_parts = [variant.format_id, resolution, variant.ext]
        if variant.stream_type == "video-only":
            label_parts = [variant.format_id, "仅视频", resolution, variant.ext]
        elif variant.stream_type == "audio-only":
            label_parts = [variant.format_id, "仅音频", variant.ext]

        label = " / ".join(part for part in label_parts if part)
        if variant.filesize:
            label += f" ({_human_size(variant.filesize)})"

        raw_formats.append(
            VideoFormat(
                format_id=variant.format_id,
                label=label,
                ext=variant.ext,
                resolution=resolution,
                filesize=variant.filesize,
                height=variant.height,
                width=variant.width,
                kind="raw",
                type=variant.stream_type,
                watermark_hint=format_watermark_hint,
            )
        )

    formats = _build_resolution_presets(available_heights)
    formats.extend(raw_formats)

    if not formats:
        formats.append(
            VideoFormat(
                format_id="best",
                label="推荐下载",
                quality_label="推荐",
                kind="recommended",
            )
        )

    return ParseResponse(
        url=url,
        title=info.title,
        cover_url=info.cover_url,
        duration_seconds=info.duration_seconds,
        source_site=platform_profile.display_name if platform_profile else _source_site_name(extractor),
        platform_id=platform_profile.id if platform_profile else None,
        platform_category=platform_profile.category if platform_profile else None,
        compliance_note=platform_profile.compliance_note if platform_profile else None,
        extractor=extractor,
        watermark_hint=_derive_response_watermark_hint(extractor, platform_profile),
        formats=formats,
    )


def _build_resolution_presets(available_heights: set[int]) -> list[VideoFormat]:
    formats = [
        VideoFormat(
            format_id=RECOMMENDED_FORMAT_ID,
            label="推荐下载 / 自动选择最佳音视频并合并",
            quality_label="推荐",
            ext="mp4",
            kind="recommended",
            note="自动选择当前来源可用的最佳音视频并合并。",
        )
    ]
    for height, label in RESOLUTION_PRESETS:
        can_match = any(h >= height for h in available_heights)
        if can_match:
            higher = [h for h in available_heights if h > height]
            if higher:
                note = f"该来源最高可用 {max(higher)}p，将自动降级下载。"
            else:
                note = "该清晰度有可用源，将直接下载，不做后端转码。"
        else:
            note = "该来源未提供此清晰度或更高的视频流，不可选择。"
        formats.append(
            VideoFormat(
                format_id=f"bv*[height<={height}]+ba/b[height<={height}]",
                label=f"{label} / 文件更小，通常下载更快",
                quality_label=label,
                ext="mp4",
                resolution=f"最高 {height}p",
                height=height,
                kind="video",
                available=can_match,
                note=note,
            )
        )
    return formats


def _human_size(size: int) -> str:
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    if size < 1024 * 1024 * 1024:
        return f"{size / (1024 * 1024):.1f} MB"
    return f"{size / (1024 * 1024 * 1024):.1f} GB"


def _source_site_name(extractor: str | None) -> str | None:
    if not extractor:
        return None
    normalized = extractor.lower()
    for key, label in SOURCE_SITE_NAMES.items():
        if normalized.startswith(key):
            return label
    return extractor


def _derive_format_watermark_hint(extractor: str | None) -> str | None:
    if not extractor:
        return None
    if extractor in _WATERMARK_FREE_EXTRACTORS:
        return "优先可用源"
    if extractor in _WATERMARK_PLATFORM_EXTRACTORS:
        return "可能含平台水印"
    return "不可确认"


def _derive_response_watermark_hint(
    extractor: str | None,
    platform_profile: Any | None,
) -> str | None:
    if not extractor:
        return None
    if extractor in _WATERMARK_FREE_EXTRACTORS:
        return "优先可用源"
    if extractor in _WATERMARK_PLATFORM_EXTRACTORS:
        return "可能含平台水印"
    return "不可确认"
