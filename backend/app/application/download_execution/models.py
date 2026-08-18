from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from enum import StrEnum
from pathlib import Path


class ExecutionDisposition(StrEnum):
    ACK = "ack"
    REQUEUE = "requeue"


@dataclass(frozen=True, slots=True)
class DownloadExecutionSettings:
    worker_id: str
    bucket: str
    workspace_root: Path
    lease_for: timedelta
    heartbeat_interval: float
    max_file_size_bytes: int

    def __post_init__(self) -> None:
        if not self.worker_id.strip() or not self.bucket.strip():
            raise ValueError("worker id and bucket cannot be blank")
        if self.lease_for.total_seconds() <= 0 or self.heartbeat_interval <= 0:
            raise ValueError("lease and heartbeat interval must be positive")
        if self.heartbeat_interval >= self.lease_for.total_seconds():
            raise ValueError("heartbeat interval must be shorter than the lease")
        if self.max_file_size_bytes <= 0:
            raise ValueError("artifact size limit must be positive")
        object.__setattr__(self, "workspace_root", self.workspace_root.resolve())


@dataclass(frozen=True, slots=True)
class ArtifactDetails:
    bucket: str
    sha256: str
    size_bytes: int
    duration_ms: int
    container: str
    content_type: str
    media_metadata: dict[str, object]
