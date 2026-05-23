from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path


class WorkerStage(StrEnum):
    START = "start"
    DOWNLOAD = "download"
    PROBE = "probe"
    UPLOAD = "upload"
    AI = "ai"
    CLEANUP = "cleanup"


class WorkerFailureCode(StrEnum):
    DOWNLOAD_FAILED = "download_failed"
    FORMAT_UNAVAILABLE = "format_unavailable"
    FILE_TOO_LARGE = "file_too_large"
    MEDIA_TOOLS_MISSING = "media_tools_missing"
    FFPROBE_FAILED = "ffprobe_failed"
    STORAGE_FAILED = "storage_failed"
    TASK_TIMEOUT = "task_timeout"
    TASK_CANCELED = "task_canceled"
    PLATFORM_RESTRICTED = "platform_restricted"
    PLATFORM_RATE_LIMITED = "platform_rate_limited"
    UNSUPPORTED_PLATFORM = "unsupported_platform"
    BROWSER_COOKIES_UNAVAILABLE = "browser_cookies_unavailable"


class AIProcessStatus(StrEnum):
    SKIPPED = "skipped"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True)
class WorkerContext:
    task_id: str
    user_id: int
    source_url: str
    format_id: str
    title: str
    work_dir: Path
    max_file_size_bytes: int
    file_retention_hours: int


@dataclass(frozen=True)
class DownloadArtifact:
    path: Path
    filename: str
    size_bytes: int
    content_type: str = "application/octet-stream"


@dataclass(frozen=True)
class StoredArtifact:
    object_key: str
    object_size: int
    expires_at: datetime


@dataclass(frozen=True)
class FailureInfo:
    code: WorkerFailureCode
    reason: str
    stage: WorkerStage
    retryable: bool


@dataclass(frozen=True)
class AIProcessResult:
    status: AIProcessStatus
    summary: str | None = None
    mindmap: str | None = None
    error: str | None = None
