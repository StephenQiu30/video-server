"""Fail-closed verification for one browser-uploaded MP4 object."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import math
import os
import re
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Protocol

from app.application.import_execution import (
    ImportVerificationClaim,
    ImportVerificationRejected,
    VerifiedImportArtifact,
)
from app.domain.imports import ContentKind, ImportErrorCode, ImportSourceFormat

_MP4_BRANDS = frozenset(
    {
        b"avc1",
        b"cmfc",
        b"cmfs",
        b"dash",
        b"iso2",
        b"iso3",
        b"iso4",
        b"iso5",
        b"iso6",
        b"iso7",
        b"iso8",
        b"iso9",
        b"isom",
        b"M4V ",
        b"mp41",
        b"mp42",
        b"MSNV",
    }
)
_CONTAINER_BOXES = frozenset(
    {
        b"dinf",
        b"edts",
        b"mdia",
        b"meco",
        b"meta",
        b"mfra",
        b"minf",
        b"moof",
        b"moov",
        b"mvex",
        b"schi",
        b"sinf",
        b"stbl",
        b"traf",
        b"trak",
        b"tref",
        b"udta",
    }
)
_CODEC = re.compile(r"^[a-z0-9][a-z0-9_.-]{0,63}$")
_READ_CHUNK = 1024 * 1024


class VideoVerificationError(ImportVerificationRejected):
    """A stable validation failure safe to map to an import error code."""

    pass


@dataclass(frozen=True, slots=True)
class VideoProbeStream:
    codec_type: str
    codec_name: str
    width: int | None = None
    height: int | None = None


@dataclass(frozen=True, slots=True)
class VideoProbeResult:
    format_names: frozenset[str]
    duration_seconds: float
    streams: tuple[VideoProbeStream, ...]


@dataclass(frozen=True, slots=True)
class VerifiedVideo:
    path: Path
    size_bytes: int
    sha256: str
    duration_ms: int
    video_streams: int
    audio_streams: int
    codecs: tuple[str, ...]
    width: int
    height: int

    @property
    def media_metadata(self) -> dict[str, object]:
        return {
            "audio_streams": self.audio_streams,
            "codecs": list(self.codecs),
            "height": self.height,
            "video_streams": self.video_streams,
            "width": self.width,
        }


@dataclass(frozen=True, slots=True)
class VideoVerificationSettings:
    ffprobe_binary: Path
    ffprobe_timeout_seconds: float
    max_probe_output_bytes: int
    max_size_bytes: int
    max_duration_seconds: int
    max_width: int = 8192
    max_height: int = 8192
    max_streams: int = 32
    max_boxes: int = 100_000

    def __post_init__(self) -> None:
        if (
            self.ffprobe_timeout_seconds <= 0
            or self.max_probe_output_bytes < 1024
            or self.max_size_bytes <= 0
            or self.max_duration_seconds <= 0
            or self.max_width <= 0
            or self.max_height <= 0
            or not 1 <= self.max_streams <= 1024
            or not 16 <= self.max_boxes <= 1_000_000
        ):
            raise ValueError("invalid video verification limits")


class VideoProbe(Protocol):
    async def probe(
        self, path: Path, settings: VideoVerificationSettings
    ) -> VideoProbeResult: ...


async def verify_video(
    path: Path,
    *,
    workspace_root: Path,
    declared_size_bytes: int,
    declared_sha256: str,
    settings: VideoVerificationSettings,
    probe: VideoProbe,
) -> VerifiedVideo:
    """Verify immutable bytes and bounded media metadata without network access."""
    if re.fullmatch(r"[0-9a-f]{64}", declared_sha256) is None:
        raise VideoVerificationError(
            ImportErrorCode.SHA256_MISMATCH, "declared video digest is invalid"
        )
    safe_path, size_bytes = _safe_regular_file(
        path,
        workspace_root,
        declared_size_bytes=declared_size_bytes,
        max_size_bytes=settings.max_size_bytes,
    )
    digest = await asyncio.to_thread(_sha256, safe_path)
    if not hmac.compare_digest(digest, declared_sha256):
        raise VideoVerificationError(
            ImportErrorCode.SHA256_MISMATCH, "video digest does not match declaration"
        )
    await asyncio.to_thread(_verify_bmff, safe_path, size_bytes, settings.max_boxes)
    try:
        metadata = await probe.probe(safe_path, settings)
    except VideoVerificationError:
        raise
    except Exception as exc:
        raise VideoVerificationError(
            ImportErrorCode.VIDEO_INVALID, "ffprobe could not validate the video"
        ) from exc
    video_streams = tuple(
        stream for stream in metadata.streams if stream.codec_type == "video"
    )
    audio_streams = sum(stream.codec_type == "audio" for stream in metadata.streams)
    if (
        "mp4" not in metadata.format_names
        or not math.isfinite(metadata.duration_seconds)
        or metadata.duration_seconds <= 0
        or metadata.duration_seconds > settings.max_duration_seconds
        or not video_streams
        or len(metadata.streams) > settings.max_streams
    ):
        raise VideoVerificationError(
            ImportErrorCode.VIDEO_INVALID, "video media metadata is outside policy"
        )
    for stream in metadata.streams:
        if stream.codec_type not in {"video", "audio", "subtitle"}:
            raise VideoVerificationError(
                ImportErrorCode.VIDEO_INVALID, "active or unsupported stream detected"
            )
    for stream in video_streams:
        if (
            _CODEC.fullmatch(stream.codec_name) is None
            or stream.codec_name == "unknown"
            or type(stream.width) is not int
            or type(stream.height) is not int
            or not 1 <= stream.width <= settings.max_width
            or not 1 <= stream.height <= settings.max_height
        ):
            raise VideoVerificationError(
                ImportErrorCode.VIDEO_INVALID, "video stream metadata is invalid"
            )
    return VerifiedVideo(
        path=safe_path,
        size_bytes=size_bytes,
        sha256=digest,
        duration_ms=max(1, round(metadata.duration_seconds * 1000)),
        video_streams=len(video_streams),
        audio_streams=audio_streams,
        codecs=tuple(sorted({stream.codec_name for stream in metadata.streams})),
        width=max(stream.width for stream in video_streams if stream.width is not None),
        height=max(
            stream.height for stream in video_streams if stream.height is not None
        ),
    )


class FfprobeVideoProbe:
    async def probe(
        self, path: Path, settings: VideoVerificationSettings
    ) -> VideoProbeResult:
        command = (
            str(settings.ffprobe_binary),
            "-v",
            "error",
            "-max_alloc",
            str(64 * 1024**2),
            "-protocol_whitelist",
            "file",
            "-show_entries",
            "format=format_name,duration:stream=codec_type,codec_name,width,height",
            "-of",
            "json",
            "-i",
            str(path),
        )
        environment = _probe_environment(path.parent)
        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                cwd=path.parent,
                env=environment,
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except OSError as exc:
            raise VideoVerificationError(
                ImportErrorCode.VIDEO_INVALID, "ffprobe is unavailable"
            ) from exc
        try:
            stdout, stderr = await asyncio.wait_for(
                _bounded_output(process, settings.max_probe_output_bytes),
                timeout=settings.ffprobe_timeout_seconds,
            )
        except TimeoutError as exc:
            await _terminate(process)
            raise VideoVerificationError(
                ImportErrorCode.VIDEO_INVALID, "ffprobe timed out"
            ) from exc
        except asyncio.CancelledError:
            await asyncio.shield(_terminate(process))
            raise
        except _ProbeOutputExceeded as exc:
            await _terminate(process)
            raise VideoVerificationError(
                ImportErrorCode.VIDEO_INVALID, "ffprobe output exceeded its budget"
            ) from exc
        if process.returncode != 0 or stderr:
            raise VideoVerificationError(
                ImportErrorCode.VIDEO_INVALID, "ffprobe rejected the video"
            )
        return _parse_probe(stdout, settings.max_streams)


class Mp4ImportVerifier:
    def __init__(
        self,
        workspace_root: Path,
        settings: VideoVerificationSettings,
        *,
        probe: VideoProbe | None = None,
    ) -> None:
        self._workspace_root = workspace_root.resolve()
        self._settings = settings
        self._probe = probe or FfprobeVideoProbe()

    async def __call__(
        self, path: Path, claim: ImportVerificationClaim
    ) -> VerifiedImportArtifact:
        if (
            claim.content_kind is not ContentKind.VIDEO
            or claim.source_format is not ImportSourceFormat.MP4
        ):
            raise VideoVerificationError(
                ImportErrorCode.VIDEO_INVALID, "unsupported video import contract"
            )
        verified = await verify_video(
            path,
            workspace_root=self._workspace_root,
            declared_size_bytes=claim.declared_size_bytes,
            declared_sha256=claim.declared_sha256,
            settings=self._settings,
            probe=self._probe,
        )
        return VerifiedImportArtifact(
            sha256=verified.sha256,
            size_bytes=verified.size_bytes,
            duration_ms=verified.duration_ms,
            container="mp4",
            content_type="video/mp4",
            media_metadata=verified.media_metadata,
        )


def _safe_regular_file(
    path: Path,
    workspace_root: Path,
    *,
    declared_size_bytes: int,
    max_size_bytes: int,
) -> tuple[Path, int]:
    try:
        root_stat = workspace_root.lstat()
        parent_stat = path.parent.lstat()
        file_stat = path.lstat()
        root = workspace_root.resolve(strict=True)
        parent = path.parent.resolve(strict=True)
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise VideoVerificationError(
            ImportErrorCode.VIDEO_INVALID, "video workspace is unavailable"
        ) from exc
    if (
        not stat.S_ISDIR(root_stat.st_mode)
        or stat.S_ISLNK(root_stat.st_mode)
        or not stat.S_ISDIR(parent_stat.st_mode)
        or stat.S_ISLNK(parent_stat.st_mode)
        or not stat.S_ISREG(file_stat.st_mode)
        or stat.S_ISLNK(file_stat.st_mode)
        or not parent.is_relative_to(root)
        or parent.parent != root
        or resolved.parent != parent
    ):
        raise VideoVerificationError(
            ImportErrorCode.VIDEO_INVALID, "video path is outside the private workspace"
        )
    size_bytes = file_stat.st_size
    if (
        isinstance(declared_size_bytes, bool)
        or size_bytes <= 0
        or size_bytes != declared_size_bytes
        or size_bytes > max_size_bytes
    ):
        raise VideoVerificationError(
            ImportErrorCode.SIZE_MISMATCH, "video size does not match declaration"
        )
    return resolved, size_bytes


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(_READ_CHUNK), b""):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass(slots=True)
class _BoxBudget:
    remaining: int

    def consume(self) -> None:
        self.remaining -= 1
        if self.remaining < 0:
            raise VideoVerificationError(
                ImportErrorCode.VIDEO_INVALID, "BMFF box count exceeded its budget"
            )


def _verify_bmff(path: Path, file_size: int, max_boxes: int) -> None:
    budget = _BoxBudget(max_boxes)
    with path.open("rb") as source:
        top_level = tuple(_boxes(source, 0, file_size, budget))
        types = tuple(box_type for box_type, _, _ in top_level)
        if (
            types.count(b"ftyp") != 1
            or types.count(b"moov") != 1
            or b"mdat" not in types
        ):
            raise VideoVerificationError(
                ImportErrorCode.VIDEO_INVALID, "file is not a single MP4 container"
            )
        ftyp_index = types.index(b"ftyp")
        if ftyp_index > 1:
            raise VideoVerificationError(
                ImportErrorCode.VIDEO_INVALID, "MP4 file type box is misplaced"
            )
        _, ftyp_start, ftyp_end = top_level[ftyp_index]
        _verify_ftyp(source, ftyp_start, ftyp_end)
        for box_type, payload_start, box_end in top_level:
            if box_type == b"moov":
                _verify_nested_boxes(source, payload_start, box_end, budget, depth=1)


def _verify_nested_boxes(
    source: BinaryIO,
    start: int,
    end: int,
    budget: _BoxBudget,
    *,
    depth: int,
) -> None:
    if depth > 16:
        raise VideoVerificationError(
            ImportErrorCode.VIDEO_INVALID, "BMFF nesting exceeded its budget"
        )
    for box_type, payload_start, box_end in _boxes(source, start, end, budget):
        if box_type == b"rmra":
            raise VideoVerificationError(
                ImportErrorCode.VIDEO_INVALID, "external movie reference is forbidden"
            )
        if box_type == b"dref":
            _verify_data_references(source, payload_start, box_end, budget)
            continue
        if box_type in _CONTAINER_BOXES:
            child_start = payload_start + (4 if box_type == b"meta" else 0)
            if child_start > box_end:
                raise VideoVerificationError(
                    ImportErrorCode.VIDEO_INVALID, "BMFF container is truncated"
                )
            _verify_nested_boxes(source, child_start, box_end, budget, depth=depth + 1)


def _verify_data_references(
    source: BinaryIO, start: int, end: int, budget: _BoxBudget
) -> None:
    if end - start < 8:
        raise VideoVerificationError(
            ImportErrorCode.VIDEO_INVALID, "BMFF data reference is truncated"
        )
    source.seek(start + 4)
    entry_count = int.from_bytes(source.read(4), "big")
    entries = tuple(_boxes(source, start + 8, end, budget))
    if entry_count != len(entries):
        raise VideoVerificationError(
            ImportErrorCode.VIDEO_INVALID, "BMFF data reference count is invalid"
        )
    for box_type, payload_start, box_end in entries:
        if box_type != b"url " or box_end - payload_start < 4:
            raise VideoVerificationError(
                ImportErrorCode.VIDEO_INVALID, "external data reference is forbidden"
            )
        source.seek(payload_start)
        flags = int.from_bytes(source.read(4), "big") & 0x00FF_FFFF
        if flags & 1 != 1 or box_end - payload_start != 4:
            raise VideoVerificationError(
                ImportErrorCode.VIDEO_INVALID, "external data reference is forbidden"
            )


def _verify_ftyp(source: BinaryIO, start: int, end: int) -> None:
    size = end - start
    if size < 8 or size % 4:
        raise VideoVerificationError(
            ImportErrorCode.VIDEO_INVALID, "MP4 file type box is invalid"
        )
    source.seek(start)
    payload = source.read(size)
    brands = {
        payload[:4],
        *(payload[offset : offset + 4] for offset in range(8, size, 4)),
    }
    if not brands & _MP4_BRANDS:
        raise VideoVerificationError(
            ImportErrorCode.VIDEO_INVALID, "BMFF brand is not an MP4 brand"
        )


def _boxes(
    source: BinaryIO, start: int, end: int, budget: _BoxBudget
) -> list[tuple[bytes, int, int]]:
    boxes: list[tuple[bytes, int, int]] = []
    position = start
    while position < end:
        if end - position < 8:
            raise VideoVerificationError(
                ImportErrorCode.VIDEO_INVALID, "BMFF box header is truncated"
            )
        source.seek(position)
        header = source.read(8)
        if len(header) != 8:
            raise VideoVerificationError(
                ImportErrorCode.VIDEO_INVALID, "BMFF box header is unavailable"
            )
        size = int.from_bytes(header[:4], "big")
        box_type = header[4:]
        header_size = 8
        if size == 1:
            extended = source.read(8)
            if len(extended) != 8:
                raise VideoVerificationError(
                    ImportErrorCode.VIDEO_INVALID, "BMFF large box is truncated"
                )
            size = int.from_bytes(extended, "big")
            header_size = 16
        elif size == 0:
            size = end - position
        if size < header_size or position + size > end:
            raise VideoVerificationError(
                ImportErrorCode.VIDEO_INVALID, "BMFF box size is invalid"
            )
        budget.consume()
        boxes.append((box_type, position + header_size, position + size))
        position += size
    return boxes


class _ProbeOutputExceeded(RuntimeError):
    pass


async def _bounded_output(
    process: asyncio.subprocess.Process, limit: int
) -> tuple[bytes, bytes]:
    if process.stdout is None or process.stderr is None:
        raise RuntimeError("ffprobe pipes are unavailable")
    stdout_task = asyncio.create_task(_read_limited(process.stdout, limit))
    stderr_task = asyncio.create_task(_read_limited(process.stderr, limit))
    try:
        stdout, stderr = await asyncio.gather(stdout_task, stderr_task)
        await process.wait()
        return stdout, stderr
    except BaseException:
        stdout_task.cancel()
        stderr_task.cancel()
        await asyncio.gather(stdout_task, stderr_task, return_exceptions=True)
        raise


async def _read_limited(reader: asyncio.StreamReader, limit: int) -> bytes:
    output = bytearray()
    while True:
        remaining = limit + 1 - len(output)
        if remaining <= 0:
            raise _ProbeOutputExceeded
        chunk = await reader.read(min(64 * 1024, remaining))
        if not chunk:
            break
        output.extend(chunk)
        if len(output) > limit:
            raise _ProbeOutputExceeded
    return bytes(output)


async def _terminate(process: asyncio.subprocess.Process) -> None:
    if process.returncode is not None:
        return
    process.kill()
    await process.wait()


def _parse_probe(payload: bytes, max_streams: int) -> VideoProbeResult:
    try:
        document = json.loads(payload)
        allowed_root = {"streams", "format", "programs", "stream_groups"}
        if (
            not isinstance(document, dict)
            or not {"streams", "format"} <= set(document)
            or not set(document) <= allowed_root
            or document.get("programs", []) != []
            or document.get("stream_groups", []) != []
        ):
            raise TypeError
        raw_streams = document["streams"]
        raw_format = document["format"]
        if (
            not isinstance(raw_streams, list)
            or len(raw_streams) > max_streams
            or not isinstance(raw_format, dict)
            or set(raw_format) != {"format_name", "duration"}
        ):
            raise TypeError
        format_name = raw_format["format_name"]
        duration = raw_format["duration"]
        if not isinstance(format_name, str) or not isinstance(duration, str):
            raise TypeError
        streams = tuple(_parse_stream(stream) for stream in raw_streams)
        return VideoProbeResult(
            format_names=frozenset(format_name.split(",")),
            duration_seconds=float(duration),
            streams=streams,
        )
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise VideoVerificationError(
            ImportErrorCode.VIDEO_INVALID, "ffprobe returned invalid metadata"
        ) from exc


def _parse_stream(value: object) -> VideoProbeStream:
    if not isinstance(value, dict):
        raise TypeError
    allowed = {"codec_type", "codec_name", "width", "height"}
    if not set(value) <= allowed or not {"codec_type", "codec_name"} <= set(value):
        raise TypeError
    codec_type = value["codec_type"]
    codec_name = value["codec_name"]
    width = value.get("width")
    height = value.get("height")
    if (
        not isinstance(codec_type, str)
        or not isinstance(codec_name, str)
        or (width is not None and type(width) is not int)
        or (height is not None and type(height) is not int)
    ):
        raise TypeError
    return VideoProbeStream(codec_type, codec_name, width, height)


def _probe_environment(workspace: Path) -> dict[str, str]:
    environment = {
        "LANG": "C",
        "LC_ALL": "C",
        "PATH": os.environ.get("PATH", ""),
        "TEMP": str(workspace),
        "TMP": str(workspace),
        "TMPDIR": str(workspace),
    }
    system_root = os.environ.get("SystemRoot")
    if system_root:
        environment["SystemRoot"] = system_root
    return environment
