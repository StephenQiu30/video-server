from __future__ import annotations

import json
import logging
from pathlib import Path

from worker.domain import EnhancedArtifactsResult, EnhancedArtifactsStatus

logger = logging.getLogger(__name__)

METADATA_KEYS = (
    "description",
    "uploader",
    "upload_date",
    "duration",
    "view_count",
    "like_count",
    "tags",
    "categories",
)


def collect_enhanced_artifacts(
    info_dict: dict,
    work_dir: Path,
) -> EnhancedArtifactsResult:
    """Collect subtitles and metadata from a yt-dlp info dict.

    Failures are swallowed — this function never raises.
    Returns an :class:`EnhancedArtifactsResult` reflecting what was collected.
    """
    try:
        subtitle_data = _extract_subtitles(info_dict, work_dir)
        video_metadata = _extract_metadata(info_dict)

        has_subtitle = subtitle_data is not None
        has_metadata = video_metadata is not None

        if has_subtitle and has_metadata:
            status = EnhancedArtifactsStatus.COLLECTED
        elif has_subtitle or has_metadata:
            status = EnhancedArtifactsStatus.PARTIAL
        else:
            status = EnhancedArtifactsStatus.UNAVAILABLE

        return EnhancedArtifactsResult(
            status=status,
            subtitle_data=subtitle_data,
            video_metadata=video_metadata,
        )
    except Exception:
        logger.exception("增强产物采集异常")
        return EnhancedArtifactsResult(status=EnhancedArtifactsStatus.UNAVAILABLE)


def _extract_subtitles(info_dict: dict, work_dir: Path) -> dict | None:
    """Extract subtitle content from yt-dlp result."""
    raw = info_dict.get("subtitles") or {}
    if not isinstance(raw, dict):
        return None

    collected: dict = {}
    for lang, entries in raw.items():
        if not isinstance(entries, list):
            continue
        for entry in entries:
            ext = entry.get("ext", "")
            if ext not in ("srt", "vtt", "json3"):
                continue
            content = _read_subtitle_content(entry, work_dir)
            if content:
                collected[lang] = {"ext": ext, "content": content}
                break  # take first usable format per language

    return collected or None


def _read_subtitle_content(entry: dict, work_dir: Path) -> str | None:
    """Read subtitle content from a local file path or data URI."""
    filename = entry.get("_filename")
    if filename:
        try:
            return Path(filename).read_text(encoding="utf-8")
        except OSError:
            logger.debug("无法读取字幕文件: %s", filename)

    data = entry.get("data")
    if isinstance(data, str) and data:
        return data

    return None


def _extract_metadata(info_dict: dict) -> dict | None:
    """Extract common metadata fields from yt-dlp result."""
    metadata: dict = {}
    for key in METADATA_KEYS:
        value = info_dict.get(key)
        if value is not None:
            metadata[key] = value
    return metadata or None
