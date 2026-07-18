"""Fail-closed revision-0004 migration preflights."""

from __future__ import annotations

from alembic import op

_UPGRADE_CONSTRAINT = "ck_owner_uuid_migration_requires_empty_aggregate"
_DOWNGRADE_CONSTRAINT = "ck_identity_downgrade_requires_empty"


def require_empty_legacy_aggregate_for_upgrade() -> None:
    """Lock legacy aggregates and reject every persisted textual owner."""

    op.execute(
        """
        LOCK TABLE
            jobs,
            source_resolution_requests,
            job_events,
            outbox_messages
        IN ACCESS EXCLUSIVE MODE
        """
    )
    op.execute(
        f"""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM jobs)
                OR EXISTS (SELECT 1 FROM source_resolution_requests)
                OR EXISTS (SELECT 1 FROM job_events)
                OR EXISTS (SELECT 1 FROM outbox_messages)
            THEN
                RAISE EXCEPTION 'legacy aggregate owners require an explicit user mapping'
                    USING ERRCODE = '23514',
                        CONSTRAINT = '{_UPGRADE_CONSTRAINT}';
            END IF;
        END;
        $$
        """
    )


def require_empty_identity_for_downgrade() -> None:
    """Lock identity storage and reject schema loss once any fact exists."""

    op.execute(
        """
        LOCK TABLE
            users,
            access_tokens,
            jobs,
            source_resolution_requests,
            job_events,
            outbox_messages
        IN ACCESS EXCLUSIVE MODE
        """
    )
    op.execute(
        f"""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM users)
                OR EXISTS (SELECT 1 FROM access_tokens)
                OR EXISTS (SELECT 1 FROM jobs)
                OR EXISTS (SELECT 1 FROM source_resolution_requests)
                OR EXISTS (SELECT 1 FROM job_events)
                OR EXISTS (SELECT 1 FROM outbox_messages)
            THEN
                RAISE EXCEPTION 'identity facts prevent schema downgrade'
                    USING ERRCODE = '23514',
                        CONSTRAINT = '{_DOWNGRADE_CONSTRAINT}';
            END IF;
        END;
        $$
        """
    )
