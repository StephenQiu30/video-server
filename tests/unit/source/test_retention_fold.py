from __future__ import annotations

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from video_server.source.retention import RetentionClass, retention_deadlines

NEW_YORK = ZoneInfo("America/New_York")


def test_published_outbox_rejects_absolute_time_before_creation_across_fold() -> None:
    created_at = datetime(2026, 11, 1, 1, 10, tzinfo=NEW_YORK, fold=1)
    published_at = datetime(2026, 11, 1, 1, 50, tzinfo=NEW_YORK, fold=0)
    assert published_at.astimezone(UTC) < created_at.astimezone(UTC)

    with pytest.raises(ValueError, match="precede"):
        retention_deadlines(
            RetentionClass.PUBLISHED_OUTBOX,
            created_at=created_at,
            published_at=published_at,
        )


def test_published_outbox_accepts_absolute_time_after_creation_across_fold() -> None:
    created_at = datetime(2026, 11, 1, 1, 50, tzinfo=NEW_YORK, fold=0)
    published_at = datetime(2026, 11, 1, 1, 10, tzinfo=NEW_YORK, fold=1)
    published_utc = published_at.astimezone(UTC)
    assert published_utc > created_at.astimezone(UTC)

    deadlines = retention_deadlines(
        RetentionClass.PUBLISHED_OUTBOX,
        created_at=created_at,
        published_at=published_at,
    )

    assert deadlines.eligible_at == published_utc + timedelta(hours=22)
    assert deadlines.must_purge_by == published_utc + timedelta(hours=24)
