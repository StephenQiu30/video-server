from typing import Any

from pydantic import ValidationError

from app.core.errors import AppError
from app.schemas import ParseResponse, VideoFormat

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
    "tiktok": "TikTok",
    "xiaohongshu": "小红书",
    "ixigua": "西瓜视频",
    "youtube": "YouTube",
    "vimeo": "Vimeo",
    "dailymotion": "Dailymotion",
    "weibo": "微博",
}


class DownloadEngineAdapter:
    """Thin boundary around yt-dlp so platform-specific logic does not leak into API code."""

    def parse(self, url: str) -> ParseResponse:
        try:
            from yt_dlp import YoutubeDL
            from yt_dlp.utils import DownloadError
        except ModuleNotFoundError as exc:
            raise AppError("engine_unavailable", "下载内核未安装，请在容器环境中运行", 503) from exc

        options = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "noplaylist": True,
        }
        try:
            with YoutubeDL(options) as ydl:
                info = ydl.extract_info(url, download=False)
        except DownloadError as exc:
            raise AppError("parse_failed", "公开视频解析失败或平台暂不支持", 422) from exc
        except Exception as exc:
            raise AppError("parse_failed", "公开视频解析失败或平台暂不支持", 422) from exc

        try:
            return self._to_response(url, info or {})
        except (TypeError, ValueError, ValidationError) as exc:
            raise AppError("parse_failed", "解析结果格式暂不兼容，请稍后重试或更新下载内核", 422) from exc

    def _to_response(self, url: str, info: dict[str, Any]) -> ParseResponse:
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
            label_parts = [format_id]
            if raw.get("vcodec") == "none":
                label_parts.append("仅音频")
            elif raw.get("acodec") == "none":
                label_parts.append("仅视频")
            if resolution:
                label_parts.append(str(resolution))
            if ext:
                label_parts.append(str(ext))
            raw_formats.append(
                VideoFormat(
                    format_id=format_id,
                    label=" / ".join(label_parts),
                    ext=ext,
                    resolution=resolution,
                    filesize=filesize,
                    height=height,
                    width=width,
                    kind="raw",
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
            source_site=_source_site_name(info),
            extractor=_safe_str(info.get("extractor_key") or info.get("extractor")),
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
