"""Pure retention deadline policy."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
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


def retention_deadlines(
    retention_class: RetentionClass,
    *,
    created_at: datetime,
    published_at: datetime | None = None,
) -> RetentionDeadlines:
    raise NotImplementedError("retention deadlines are not implemented")


def classify_retention(deadline: RetentionDeadlines, *, now: datetime) -> RetentionStatus:
    raise NotImplementedError("retention classification is not implemented")
