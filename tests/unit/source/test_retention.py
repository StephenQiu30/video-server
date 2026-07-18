from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from video_server.source.retention import (
    RetentionClass,
    RetentionStatus,
    classify_retention,
    retention_deadlines,
)

CREATED_AT = datetime(2026, 7, 18, 8, 30, tzinfo=UTC)
PUBLISHED_AT = datetime(2026, 7, 18, 9, 45, tzinfo=UTC)


@pytest.mark.parametrize(
    "retention_class",
    [
        RetentionClass.RESOLUTION_DETAIL,
        RetentionClass.UNPUBLISHED_OUTBOX,
        RetentionClass.DEAD_LETTER_OUTBOX,
    ],
)
def test_resolution_details_use_absolute_seven_day_request_deadline(
    retention_class: RetentionClass,
) -> None:
    deadline = retention_deadlines(retention_class, created_at=CREATED_AT)

    assert deadline.eligible_at == CREATED_AT + timedelta(days=6, hours=22)
    assert deadline.must_purge_by == CREATED_AT + timedelta(days=7)


def test_published_outbox_deadline_is_based_on_publish_time() -> None:
    deadline = retention_deadlines(
        RetentionClass.PUBLISHED_OUTBOX,
        created_at=CREATED_AT,
        published_at=PUBLISHED_AT,
    )

    assert deadline.eligible_at == PUBLISHED_AT + timedelta(hours=22)
    assert deadline.must_purge_by == PUBLISHED_AT + timedelta(hours=24)


def test_minimal_audit_uses_absolute_30_day_request_deadline() -> None:
    deadline = retention_deadlines(
        RetentionClass.RESOLUTION_AUDIT,
        created_at=CREATED_AT,
    )

    assert deadline.eligible_at == CREATED_AT + timedelta(days=29, hours=22)
    assert deadline.must_purge_by == CREATED_AT + timedelta(days=30)


def test_present_row_warns_at_eligible_and_fails_health_at_must_purge() -> None:
    deadline = retention_deadlines(
        RetentionClass.RESOLUTION_DETAIL,
        created_at=CREATED_AT,
    )

    assert (
        classify_retention(deadline, now=deadline.eligible_at - timedelta(microseconds=1))
        is RetentionStatus.RETAIN
    )
    assert classify_retention(deadline, now=deadline.eligible_at) is RetentionStatus.ELIGIBLE_ALERT
    assert (
        classify_retention(deadline, now=deadline.must_purge_by)
        is RetentionStatus.MUST_PURGE_VIOLATION
    )


def test_published_outbox_requires_publish_time() -> None:
    with pytest.raises(ValueError, match="published_at"):
        retention_deadlines(
            RetentionClass.PUBLISHED_OUTBOX,
            created_at=CREATED_AT,
        )


def test_deadline_inputs_must_be_timezone_aware() -> None:
    with pytest.raises(ValueError, match="timezone"):
        retention_deadlines(
            RetentionClass.RESOLUTION_DETAIL,
            created_at=CREATED_AT.replace(tzinfo=None),
        )
