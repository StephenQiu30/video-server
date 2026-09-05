"""One outbox payload for initial download creation and crash recovery."""

from datetime import datetime
from uuid import uuid4

from .models import DownloadJobRow, OutboxEventRow


def requested_event(row: DownloadJobRow, now: datetime) -> OutboxEventRow:
    return OutboxEventRow(
        id=uuid4(),
        aggregate_type="download_job",
        aggregate_id=row.id,
        event_type="download.requested",
        payload={
            "job_id": str(row.id),
            "attempt": row.attempt or 0,
            "version": row.version or 0,
        },
        available_at=now,
        created_at=now,
    )
