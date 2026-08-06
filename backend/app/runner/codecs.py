from __future__ import annotations

from app.domain.downloads import AudioCodecFamily, Container, VideoCodecFamily


def container_family(value: object) -> Container:
    name = str(value or "").casefold()
    if name in {"mp4", "m4a", "mov"}:
        return Container.MP4
    if name in {"webm", "mkv", "matroska"}:
        return Container.WEBM
    return Container.OTHER


def video_codec_family(value: object) -> VideoCodecFamily:
    name = str(value or "").casefold()
    if name.startswith(("avc1", "avc3", "h264")):
        return VideoCodecFamily.H264
    if name.startswith(("hev1", "hvc1", "hevc", "h265")):
        return VideoCodecFamily.HEVC
    if name.startswith(("vp9", "vp09")):
        return VideoCodecFamily.VP9
    if name.startswith(("av1", "av01")):
        return VideoCodecFamily.AV1
    return VideoCodecFamily.OTHER


def audio_codec_family(value: object) -> AudioCodecFamily:
    name = str(value or "").casefold()
    if name.startswith(("aac", "mp4a")):
        return AudioCodecFamily.AAC
    if name.startswith("opus"):
        return AudioCodecFamily.OPUS
    if name.startswith("vorbis"):
        return AudioCodecFamily.VORBIS
    return AudioCodecFamily.OTHER
