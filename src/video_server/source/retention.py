"""Pure retention deadline policy."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum


class RetentionClass(StrEnum):
    RESOLUTION_DETAIL = "resolution_detail"
    UNPUBLISHED_OUTBOX = "unpublished_outbox"
    DEAD_LETTER_OUTBOX = "dead_letter_outbox"
    PUBLISHED_OUTBOX = "published_outbox"
    RESOLUTION_AUDIT = "resolution_audit"


class RetentionStatus(StrEnum):
    RETAIN = "retain"
    ELIGIBLE_ALERT = "eligible_alert"
    MUST_PURGE_VIOLATION = "must_purge_violation"


@dataclass(frozen=True, slots=True)
class RetentionDeadlines:
    eligible_at: datetime
    must_purge_by: datetime

    def __post_init__(self) -> None:
        _require_aware(self.eligible_at, field="eligible_at")
        _require_aware(self.must_purge_by, field="must_purge_by")
        if self.eligible_at >= self.must_purge_by:
            raise ValueError("eligible_at must precede must_purge_by")


def _require_aware(value: datetime, *, field: str) -> None:
    if not isinstance(value, datetime):
        raise TypeError(f"{field} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field} must include timezone information")


def retention_deadlines(
    retention_class: RetentionClass,
    *,
    created_at: datetime,
    published_at: datetime | None = None,
) -> RetentionDeadlines:
    if not isinstance(retention_class, RetentionClass):
        raise TypeError("retention_class must be a RetentionClass")
    _require_aware(created_at, field="created_at")

    if retention_class is RetentionClass.PUBLISHED_OUTBOX:
        if published_at is None:
            raise ValueError("published_at is required for published outbox retention")
        _require_aware(published_at, field="published_at")
        created_anchor = created_at.astimezone(UTC)
        anchor = published_at.astimezone(UTC)
        if anchor < created_anchor:
            raise ValueError("published_at cannot precede created_at")
        return RetentionDeadlines(
            eligible_at=anchor + timedelta(hours=22),
            must_purge_by=anchor + timedelta(hours=24),
        )

    if published_at is not None:
        _require_aware(published_at, field="published_at")
        raise ValueError("published_at is only valid for published outbox retention")
    anchor = created_at.astimezone(UTC)
    if retention_class is RetentionClass.RESOLUTION_AUDIT:
        return RetentionDeadlines(
            eligible_at=anchor + timedelta(days=29, hours=22),
            must_purge_by=anchor + timedelta(days=30),
        )
    return RetentionDeadlines(
        eligible_at=anchor + timedelta(days=6, hours=22),
        must_purge_by=anchor + timedelta(days=7),
    )


def classify_retention(deadline: RetentionDeadlines, *, now: datetime) -> RetentionStatus:
    if not isinstance(deadline, RetentionDeadlines):
        raise TypeError("deadline must be RetentionDeadlines")
    _require_aware(now, field="now")
    if now >= deadline.must_purge_by:
        return RetentionStatus.MUST_PURGE_VIOLATION
    if now >= deadline.eligible_at:
        return RetentionStatus.ELIGIBLE_ALERT
    return RetentionStatus.RETAIN
