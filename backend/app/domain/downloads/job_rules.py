from __future__ import annotations

from datetime import datetime, timedelta

from app.domain.downloads.enums import DownloadStage, DownloadStatus
from app.domain.downloads.errors import InvalidJobTransition

_STAGES = tuple(DownloadStage)


class DownloadJobRules:
    status: DownloadStatus
    stage: DownloadStage | None
    version: int
    lease_owner: str | None
    lease_expires_at: datetime | None
    heartbeat_at: datetime | None

    def _require_active_lease(self, owner: str, now: datetime) -> None:
        self._require_status(DownloadStatus.RUNNING)
        owner = valid_owner(owner)
        valid_time(now)
        if self.lease_owner != owner:
            raise InvalidJobTransition("lease owner does not match")
        if self.lease_expires_at is None or now >= self.lease_expires_at:
            raise InvalidJobTransition("lease has expired")

    def _require_status(self, expected: DownloadStatus) -> None:
        if self.status is not expected:
            raise InvalidJobTransition(
                f"expected {expected.value}, got {self.status.value}"
            )

    def _clear_lease(self) -> None:
        self.lease_owner = None
        self.lease_expires_at = None
        self.heartbeat_at = None

    def _bump(self) -> None:
        self.version += 1


def require_linear_stage(current: DownloadStage, requested: DownloadStage) -> None:
    current_index = _STAGES.index(current)
    requested_index = _STAGES.index(requested)
    if requested_index not in {current_index, current_index + 1}:
        raise InvalidJobTransition("download stages must advance linearly")


def valid_owner(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("lease owner cannot be blank")
    return value


def valid_time(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("datetime must be timezone-aware")


def valid_duration(value: timedelta) -> None:
    if value <= timedelta(0):
        raise ValueError("lease duration must be positive")
