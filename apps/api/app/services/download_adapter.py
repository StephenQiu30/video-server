from dataclasses import dataclass
from urllib.parse import urlparse
from typing import Any

from pydantic import ValidationError

from app.core.errors import AppError
from app.schemas import ParseResponse, VideoFormat
from app.services.platforms import find_platform_profile

RECOMMENDED_FORMAT_ID = "bestvideo+bestaudio/best"
RESOLUTION_PRESETS = [
    (1080, "最高 1080p"),
    (720, "最高 720p"),
    (480, "最高 480p"),
    (360, "最高 360p"),
]
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
}


@dataclass(frozen=True)
class ParsedHost:
    raw: str
    host: str

    @classmethod
    def from_url(cls, url: str) -> "ParsedHost":
        host = (urlparse(url).hostname or "").lower()
        if not host:
            raise AppError("invalid_url", "请输入有效的视频链接", 422)
        return cls(raw=url, host=host)


class PlatformAdapter:
    """Parse adapter contract used by parse service."""

    name: str = "platform"

    def supports(self, parsed_host: ParsedHost) -> bool:
        return True

    def parse(self, url: str) -> ParseResponse:
        raise NotImplementedError

    def map_parse_error(self, exc: Exception) -> AppError:
        return AppError("parse_failed", "公开视频解析失败或平台暂不支持", 422)


class YtDlpAdapter(PlatformAdapter):
    name = "ytdlp-fallback"

    def supports(self, parsed_host: ParsedHost) -> bool:
        return True

    def parse(self, url: str) -> ParseResponse:
        info = _extract_with_ytdlp(url)
        try:
            return _to_parse_response(url, info)
        except (TypeError, ValueError, ValidationError) as exc:
            raise AppError("parse_failed", "解析结果格式暂不兼容，请稍后重试或更新下载内核", 422) from exc

    def map_parse_error(self, exc: Exception) -> AppError:
        return _classify_parse_error(exc)


class BilibiliAdapter(YtDlpAdapter):
    name = "bilibili"

    def supports(self, parsed_host: ParsedHost) -> bool:
        profile = find_platform_profile(parsed_host.raw)
        return bool(profile and profile.id == "bilibili")

    def map_parse_error(self, exc: Exception) -> AppError:
        return _classify_parse_error(exc, platform_name="B 站")


class DomesticShortVideoAdapter(YtDlpAdapter):
    name = "short-video"
    platform_ids = {"douyin", "kuaishou", "xiaohongshu", "ixigua", "weibo"}

    def supports(self, parsed_host: ParsedHost) -> bool:
        profile = find_platform_profile(parsed_host.raw)
        return bool(profile and profile.id in self.platform_ids)


class AdapterRegistry:
    def __init__(self, adapters: list[PlatformAdapter] | None = None) -> None:
        self._adapters = adapters or []
        if not self._adapters:
            self._adapters = [
                DomesticShortVideoAdapter(),
                BilibiliAdapter(),
                YtDlpAdapter(),
            ]

    def get_adapter(self, url: str) -> PlatformAdapter:
        parsed_host = ParsedHost.from_url(url)
        for adapter in self._adapters:
            if adapter.supports(parsed_host):
                return adapter
        return self._adapters[-1]


class DownloadEngineAdapter:
    """Thin boundary around video platform adapters so parsing logic is isolated."""

    def __init__(self, registry: AdapterRegistry | None = None) -> None:
        self._registry = registry or AdapterRegistry()

    def parse(self, url: str) -> ParseResponse:
        adapter = self._registry.get_adapter(url)
        try:
            return adapter.parse(url)
        except AppError:
            raise
        except Exception as exc:
            raise adapter.map_parse_error(exc) from exc

    def _to_response(self, url: str, info: dict[str, Any]) -> ParseResponse:
        return _to_parse_response(url, info)


def _extract_with_ytdlp(url: str) -> dict[str, Any]:
    try:
        from yt_dlp import YoutubeDL
    except ModuleNotFoundError as exc:
        raise AppError("engine_unavailable", "下载内核未安装，请在容器环境中运行", 503) from exc

    options = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
    }
    with YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=False)

    return info or {}


def _to_parse_response(url: str, info: dict[str, Any]) -> ParseResponse:
    platform_profile = find_platform_profile(url)
    extractor = _safe_str(info.get("extractor_key") or info.get("extractor"))
    format_watermark_hint = _derive_format_watermark_hint(extractor)
    raw_formats: list[VideoFormat] = []
    available_heights: set[int] = set()
    for raw in info.get("formats") or []:
        format_id = str(raw.get("format_id") or "")
        if not format_id:
            continue
        height = _safe_int(raw.get("height"))
        width = _safe_int(raw.get("width"))
        if height and raw.get("vcodec") != "none":
            available_heights.add(height)
        resolution = raw.get("resolution")
        if not resolution and width and height:
            resolution = f"{width}x{height}"
        ext = raw.get("ext")
        filesize = _safe_int(raw.get("filesize") or raw.get("filesize_approx"))

        vcodec = raw.get("vcodec")
        acodec = raw.get("acodec")
        # yt-dlp conventions:
        # - vcodec="none" means audio-only
        # - acodec="none" means video-only
        # - Neither means muxed (video+audio)
        if vcodec == "none":
            has_video = False
            has_audio = True
        elif acodec == "none":
            has_video = True
            has_audio = False
        else:
            has_video = vcodec is not None or (height and width)
            has_audio = acodec is not None or vcodec is None

        if has_video and has_audio:
            stream_type = "video+audio"
            label_parts = [format_id, resolution, ext]
        elif has_video:
            stream_type = "video-only"
            label_parts = [format_id, "仅视频", resolution, ext]
        elif has_audio:
            stream_type = "audio-only"
            label_parts = [format_id, "仅音频", ext]
        else:
            stream_type = None
            label_parts = [format_id, resolution, ext]

        label = " / ".join(part for part in label_parts if part)
        if filesize:
            label += f" ({_human_size(filesize)})"

        raw_formats.append(
            VideoFormat(
                format_id=format_id,
                label=label,
                ext=ext,
                resolution=resolution,
                filesize=filesize,
                height=height,
                width=width,
                kind="raw",
                type=stream_type,
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
                ext=info.get("ext"),
                kind="recommended",
            )
        )

    return ParseResponse(
        url=url,
        title=info.get("title"),
        cover_url=info.get("thumbnail"),
        duration_seconds=_safe_int(info.get("duration")),
        source_site=platform_profile.display_name if platform_profile else _source_site_name(info),
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
        matching_heights = [item for item in available_heights if item <= height]
        best_height = max(matching_heights) if matching_heights else None
        available = best_height is not None
        if not available:
            note = "该来源未提供此清晰度或更低的视频流"
        elif best_height < height:
            note = f"该来源最高可用 {best_height}p，将自动降级下载。"
        else:
            note = "选择平台已有较低清晰度源，不做后端转码。"
        formats.append(
            VideoFormat(
                format_id=f"bv*[height<={height}]+ba/b[height<={height}]",
                label=f"{label} / 文件更小，通常下载更快",
                quality_label=label,
                ext="mp4",
                resolution=f"最高 {height}p",
                height=height,
                kind="video",
                available=available,
                note=note,
            )
        )
    return formats


def _source_site_name(info: dict[str, Any]) -> str | None:
    raw = _safe_str(info.get("extractor_key") or info.get("extractor"))
    if not raw:
        return None
    normalized = raw.lower()
    for key, label in SOURCE_SITE_NAMES.items():
        if normalized.startswith(key):
            return label
    return raw


def _classify_parse_error(exc: Exception, platform_name: str | None = None) -> AppError:
    message = str(exc).lower()
    subject = f"{platform_name}内容" if platform_name else "该内容"

    restricted_markers = (
        "login required",
        "need to login",
        "sign in",
        "members-only",
        "member-only",
        "private",
        "premium",
        "paid",
        "charge",
        "drm",
        "copyright",
        "geo restricted",
        "georestricted",
        "region",
        "仅限",
        "会员",
        "付费",
        "版权",
    )
    if any(marker in message for marker in restricted_markers):
        return AppError(
            "platform_restricted",
            f"{subject}存在访问限制，当前服务不会绕过登录、会员、付费、版权、DRM 或地区限制",
            403,
        )

    rate_limit_markers = (
        "too many requests",
        "http error 429",
        "429",
        "rate limit",
        "captcha",
        "验证码",
        "频繁",
    )
    if any(marker in message for marker in rate_limit_markers):
        return AppError("platform_rate_limited", "平台访问频率受限或触发风控，请稍后再试", 429)

    unsupported_markers = (
        "unsupported url",
        "no suitable extractor",
        "no video formats found",
        "unable to extract",
    )
    if any(marker in message for marker in unsupported_markers):
        return AppError("unsupported_platform", "该链接暂不支持解析，请确认是否为公开视频链接", 422)

    unavailable_markers = (
        "timed out",
        "timeout",
        "temporary failure",
        "connection reset",
        "connection aborted",
        "network is unreachable",
    )
    if any(marker in message for marker in unavailable_markers):
        return AppError("platform_unavailable", "平台暂时不可访问或网络超时，请稍后重试", 503)

    return AppError("parse_failed", "公开视频解析失败或平台暂不支持", 422)


def _safe_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _safe_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _human_size(size_bytes: int | None) -> str | None:
    """Format byte count to human-readable string."""
    if size_bytes is None or size_bytes <= 0:
        return None
    for unit in ("B", "KB", "MB", "GB"):
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}" if unit != "B" else f"{size_bytes} B"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


# Platforms known to serve content without watermarks.
_WATERMARK_FREE_EXTRACTORS = {"BiliBili", "YouTube", "Vimeo", "Dailymotion"}

# Platforms known to embed watermarks on downloaded content.
_WATERMARK_PLATFORM_EXTRACTORS = {"Douyin", "Kuaishou"}


def _derive_format_watermark_hint(extractor: str | None) -> str | None:
    """Derive watermark hint for individual formats based on extractor."""
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
    """Derive response-level watermark hint."""
    if not extractor:
        return None
    if extractor in _WATERMARK_FREE_EXTRACTORS:
        return "优先可用源"
    if extractor in _WATERMARK_PLATFORM_EXTRACTORS:
        return "可能含平台水印"
    if platform_profile and platform_profile.compliance_note:
        return "不可确认"
    return "不可确认"
