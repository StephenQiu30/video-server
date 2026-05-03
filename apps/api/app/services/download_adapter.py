from typing import Any

from pydantic import ValidationError

from app.core.errors import AppError
from app.schemas import ParseResponse, VideoFormat

RECOMMENDED_FORMAT_ID = "bestvideo+bestaudio/best"


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
        formats: list[VideoFormat] = []
        for raw in info.get("formats") or []:
            format_id = str(raw.get("format_id") or "")
            if not format_id:
                continue
            height = raw.get("height")
            width = raw.get("width")
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
            formats.append(
                VideoFormat(
                    format_id=format_id,
                    label=" / ".join(label_parts),
                    ext=ext,
                    resolution=resolution,
                    filesize=filesize,
                )
            )

        if formats:
            formats.insert(
                0,
                VideoFormat(
                    format_id=RECOMMENDED_FORMAT_ID,
                    label="推荐下载 / 自动选择最佳音视频并合并",
                    ext="mp4",
                ),
            )

        if not formats:
            formats.append(VideoFormat(format_id="best", label="best", ext=info.get("ext")))

        return ParseResponse(
            url=url,
            title=info.get("title"),
            cover_url=info.get("thumbnail"),
            duration_seconds=_safe_int(info.get("duration")),
            formats=formats,
        )


def _safe_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None
