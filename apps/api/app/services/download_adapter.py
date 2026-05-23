from dataclasses import dataclass
from urllib.parse import urlparse
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
        message = str(exc).lower()
        if "members-only" in message:
            return AppError("platform_restricted", "该内容存在权限限制，当前账号或当前地区可能无法解析", 403)
        if "private" in message or "仅限" in message:
            return AppError("platform_restricted", "该视频不可公开访问，解析受限", 403)
        return AppError("parse_failed", "公开视频解析失败或平台暂不支持", 422)


class BilibiliAdapter(YtDlpAdapter):
    name = "bilibili"

    def supports(self, parsed_host: ParsedHost) -> bool:
        return parsed_host.host.endswith("bilibili.com") or parsed_host.host.endswith("b23.tv")

    def map_parse_error(self, exc: Exception) -> AppError:
        message = str(exc).lower()
        if "need to login" in message or "charge" in message:
            return AppError("platform_restricted", "B 站视频存在会员/版权限制，当前方式无法解析", 403)
        return super().map_parse_error(exc)


class DomesticShortVideoAdapter(YtDlpAdapter):
    name = "short-video"
    hosts = {
        "douyin.com",
        "v.douyin.com",
        "kuaishou.com",
        "v.kuaishou.com",
        "xiaohongshu.com",
        "xhslink.com",
        "ixigua.com",
    }

    def supports(self, parsed_host: ParsedHost) -> bool:
        return any(parsed_host.host == host or parsed_host.host.endswith(f".{host}") for host in self.hosts)


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

    return info or {}


def _to_parse_response(url: str, info: dict[str, Any]) -> ParseResponse:
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
