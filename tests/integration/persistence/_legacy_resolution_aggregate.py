"""Revision-0002/0003 aggregate fixture with an intentionally textual owner."""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import Engine

from tests.integration.persistence._identity import USER_ID
from tests.integration.persistence._resolution_aggregate import (
    NOW,
    insert_event,
    insert_job,
    insert_outbox,
    insert_request,
    seed_rights,
)


def insert_legacy_aggregate(
    engine: Engine,
    *,
    confirmed_at: datetime = NOW,
) -> None:
    """Insert a coherent legacy aggregate whose TEXT owner looks exactly like a UUID."""

    eligible_at = confirmed_at + timedelta(hours=166)
    must_purge_by = confirmed_at + timedelta(hours=168)
    owner_id = str(USER_ID)
    seed_rights(engine)
    with engine.begin() as connection:
        insert_job(
            connection,
            owner_id=owner_id,
            created_at=confirmed_at,
            updated_at=confirmed_at,
            detail_eligible_at=eligible_at,
            detail_must_purge_by=must_purge_by,
        )
        insert_request(
            connection,
            owner_id=owner_id,
            rights_confirmed_at=confirmed_at,
            created_at=confirmed_at,
            detail_eligible_at=eligible_at,
            detail_must_purge_by=must_purge_by,
        )
        insert_event(
            connection,
            owner_id=owner_id,
            aggregate_created_at=confirmed_at,
            occurred_at=confirmed_at,
            detail_eligible_at=eligible_at,
            detail_must_purge_by=must_purge_by,
        )
        insert_outbox(
            connection,
            owner_id=owner_id,
            aggregate_created_at=confirmed_at,
            retention_eligible_at=eligible_at,
            retention_must_purge_by=must_purge_by,
        )
