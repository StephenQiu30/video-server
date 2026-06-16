from __future__ import annotations

from typing import Any

from app.core.errors import AppError, ErrorCode
from app.sources.adapter import VideoSourceAdapter
from app.sources.models import MediaVariant, SourceCapability, SourceInfo, SourceRequest, SubtitleTrack


class YtDlpAdapter(VideoSourceAdapter):
    """Generic yt-dlp fallback adapter."""

    @property
    def name(self) -> str:
        return "ytdlp-fallback"

    def supports(self, request: SourceRequest) -> bool:
        return True

    def parse(self, request: SourceRequest) -> SourceInfo:
        raw = _extract_with_ytdlp(request.normalized_url)
        return _to_source_info(raw)

    def map_error(self, exc: Exception) -> AppError:
        return _classify_error(str(exc))


def _extract_with_ytdlp(url: str) -> dict[str, Any]:
    try:
        from yt_dlp import YoutubeDL
    except ModuleNotFoundError as exc:
        raise AppError(ErrorCode.ENGINE_UNAVAILABLE, "下载内核未安装，请在容器环境中运行", 503) from exc

    options = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
    }
    with YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=False)
    return info or {}


def _to_source_info(raw: dict[str, Any]) -> SourceInfo:
    variants: list[MediaVariant] = []
    capabilities: set[SourceCapability] = set()
    subtitles: list[SubtitleTrack] = []

    for fmt in raw.get("formats") or []:
        format_id = str(fmt.get("format_id") or "")
        if not format_id:
            continue

        height = _safe_int(fmt.get("height"))
        width = _safe_int(fmt.get("width"))
        vcodec = fmt.get("vcodec")
        acodec = fmt.get("acodec")
        ext = fmt.get("ext")
        filesize = _safe_int(fmt.get("filesize") or fmt.get("filesize_approx"))
        resolution = fmt.get("resolution")
        if not resolution and width and height:
            resolution = f"{width}x{height}"

        variant = MediaVariant(
            format_id=format_id,
            ext=ext,
            resolution=resolution,
            height=height,
            width=width,
            filesize=filesize,
            vcodec=vcodec,
            acodec=acodec,
        )
        variants.append(variant)

        if variant.stream_type in ("video+audio", "video-only"):
            capabilities.add(SourceCapability.HAS_VIDEO)
        if variant.stream_type in ("video+audio", "audio-only"):
            capabilities.add(SourceCapability.HAS_AUDIO)

    for lang, entries in (raw.get("subtitles") or {}).items():
        for entry in entries or []:
            subtitles.append(SubtitleTrack(
                language=lang,
                ext=entry.get("ext"),
                url=entry.get("url"),
            ))
    if subtitles:
        capabilities.add(SourceCapability.HAS_SUBTITLES)

    heights = {v.height for v in variants if v.height and v.stream_type != "audio-only"}
    if len(heights) > 1:
        capabilities.add(SourceCapability.MULTI_RESOLUTION)

    return SourceInfo(
        title=raw.get("title"),
        cover_url=raw.get("thumbnail"),
        duration_seconds=_safe_int(raw.get("duration")),
        extractor=_safe_str(raw.get("extractor_key") or raw.get("extractor")),
        variants=variants,
        subtitles=subtitles,
        capabilities=capabilities,
        raw_info=raw,
    )


def _classify_error(message: str) -> AppError:
    lower = message.lower()

    restricted_markers = (
        "login required", "need to login", "sign in",
        "members-only", "member-only", "private", "premium",
        "paid", "charge", "drm", "copyright",
        "geo restricted", "georestricted", "region",
        "仅限", "会员", "付费", "版权",
    )
    if any(m in lower for m in restricted_markers):
        return AppError(
            ErrorCode.PLATFORM_RESTRICTED,
            "该内容存在访问限制，当前服务不会绕过登录、会员、付费、版权、DRM 或地区限制",
            403,
        )

    rate_limit_markers = (
        "too many requests", "http error 429", "429",
        "rate limit", "captcha", "验证码", "频繁",
    )
    if any(m in lower for m in rate_limit_markers):
        return AppError(ErrorCode.PLATFORM_RATE_LIMITED, "平台访问频率受限或触发风控，请稍后再试", 429)

    unsupported_markers = (
        "unsupported url", "no suitable extractor",
        "no video formats found", "unable to extract",
    )
    if any(m in lower for m in unsupported_markers):
        return AppError(ErrorCode.UNSUPPORTED_PLATFORM, "该链接暂不支持解析，请确认是否为公开视频链接", 422)

    unavailable_markers = (
        "timed out", "timeout", "temporary failure",
        "connection reset", "connection aborted", "network is unreachable",
    )
    if any(m in lower for m in unavailable_markers):
        return AppError(ErrorCode.PLATFORM_UNAVAILABLE, "平台暂时不可访问或网络超时，请稍后重试", 503)

    return AppError(ErrorCode.PARSE_FAILED, "公开视频解析失败或平台暂不支持", 422)


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
