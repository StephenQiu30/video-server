"""SQL fixtures for the source-resolution create aggregate."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta

from sqlalchemy import Connection, Engine, text

from tests.integration.persistence._identity import USER_ID, ensure_user_for_owner
from tests.integration.persistence._rights_catalog import insert_statement

NOW = datetime(2026, 7, 18, tzinfo=UTC)
ELIGIBLE_AT = NOW + timedelta(hours=166)
MUST_PURGE_BY = NOW + timedelta(hours=168)
JOB_ID = "job_01J3H5N7Q9S1V3X5Z7A9C1E3G5"
RESOLUTION_ID = "res_01J3H5N7Q9S1V3X5Z7A9C1E3G5"
OWNER_ID = USER_ID
RIGHTS_VERSION = "rights-2026-07-18.1"
RIGHTS_LOCALE = "zh-CN"
RIGHTS_STATEMENT = f"statement-{RIGHTS_VERSION}"
RIGHTS_HASH = hashlib.sha256(RIGHTS_STATEMENT.encode()).hexdigest()


def seed_rights(engine: Engine) -> None:
    insert_statement(engine, version=RIGHTS_VERSION)


def insert_job(connection: Connection, **overrides: object) -> None:
    values: dict[str, object] = {
        "id": JOB_ID,
        "owner_id": OWNER_ID,
        "job_type": "SOURCE_RESOLUTION",
        "status": "QUEUED",
        "stage": "VALIDATING_URL",
        "attempt": 0,
        "progress": None,
        "created_at": NOW,
        "updated_at": NOW,
        "terminal_at": None,
        "detail_eligible_at": ELIGIBLE_AT,
        "detail_must_purge_by": MUST_PURGE_BY,
    }
    values.update(overrides)
    ensure_user_for_owner(connection, values["owner_id"])
    connection.execute(
        text(
            """
            INSERT INTO jobs (
                id, owner_id, job_type, status, stage, attempt, progress,
                created_at, updated_at, terminal_at,
                detail_eligible_at, detail_must_purge_by
            ) VALUES (
                :id, :owner_id, :job_type, :status, :stage, :attempt, :progress,
                :created_at, :updated_at, :terminal_at,
                :detail_eligible_at, :detail_must_purge_by
            )
            """
        ),
        values,
    )


def insert_request(connection: Connection, **overrides: object) -> None:
    values: dict[str, object] = {
        "id": RESOLUTION_ID,
        "owner_id": OWNER_ID,
        "operation": "probe",
        "job_id": JOB_ID,
        "idempotency_key_digest": "1" * 64,
        "request_digest": "2" * 64,
        "url_ciphertext": b"x" * 17,
        "url_nonce": b"n" * 24,
        "url_wrapped_dek": b"w" * 48,
        "url_wrap_nonce": b"r" * 24,
        "url_key_id": "kek-1",
        "rights_statement_version": RIGHTS_VERSION,
        "rights_statement_locale": RIGHTS_LOCALE,
        "rights_statement_sha256": RIGHTS_HASH,
        "rights_confirmed_at": NOW,
        "created_at": NOW,
        "detail_eligible_at": ELIGIBLE_AT,
        "detail_must_purge_by": MUST_PURGE_BY,
    }
    values.update(overrides)
    connection.execute(
        text(
            """
            INSERT INTO source_resolution_requests (
                id, owner_id, operation, job_id,
                idempotency_key_digest, request_digest,
                url_ciphertext, url_nonce, url_wrapped_dek, url_wrap_nonce, url_key_id,
                rights_statement_version, rights_statement_locale,
                rights_statement_sha256, rights_confirmed_at,
                created_at, detail_eligible_at, detail_must_purge_by
            ) VALUES (
                :id, :owner_id, :operation, :job_id,
                :idempotency_key_digest, :request_digest,
                :url_ciphertext, :url_nonce, :url_wrapped_dek, :url_wrap_nonce, :url_key_id,
                :rights_statement_version, :rights_statement_locale,
                :rights_statement_sha256, :rights_confirmed_at,
                :created_at, :detail_eligible_at, :detail_must_purge_by
            )
            """
        ),
        values,
    )


def insert_event(connection: Connection, **overrides: object) -> None:
    values: dict[str, object] = {
        "job_id": JOB_ID,
        "owner_id": OWNER_ID,
        "aggregate_created_at": NOW,
        "status": "QUEUED",
        "stage": "VALIDATING_URL",
        "attempt": 0,
        "progress": None,
        "occurred_at": NOW,
        "detail_eligible_at": ELIGIBLE_AT,
        "detail_must_purge_by": MUST_PURGE_BY,
    }
    values.update(overrides)
    connection.execute(
        text(
            """
            INSERT INTO job_events (
                job_id, owner_id, aggregate_created_at, status, stage, attempt, progress,
                occurred_at, detail_eligible_at, detail_must_purge_by
            ) VALUES (
                :job_id, :owner_id, :aggregate_created_at, :status, :stage, :attempt,
                :progress, :occurred_at, :detail_eligible_at, :detail_must_purge_by
            )
            """
        ),
        values,
    )


def insert_outbox(connection: Connection, **overrides: object) -> None:
    values: dict[str, object] = {
        "resolution_request_id": RESOLUTION_ID,
        "job_id": JOB_ID,
        "owner_id": OWNER_ID,
        "aggregate_created_at": NOW,
        "kind": "SOURCE_RESOLUTION_REQUESTED",
        "attempts": 0,
        "lease_version": 0,
        "retention_eligible_at": ELIGIBLE_AT,
        "retention_must_purge_by": MUST_PURGE_BY,
    }
    values.update(overrides)
    connection.execute(
        text(
            """
            INSERT INTO outbox_messages (
                resolution_request_id, job_id, owner_id, aggregate_created_at, kind,
                attempts, lease_version, retention_eligible_at, retention_must_purge_by
            ) VALUES (
                :resolution_request_id, :job_id, :owner_id, :aggregate_created_at, :kind,
                :attempts, :lease_version, :retention_eligible_at, :retention_must_purge_by
            )
            """
        ),
        values,
    )


def insert_aggregate(engine: Engine) -> None:
    seed_rights(engine)
    with engine.begin() as connection:
        insert_job(connection)
        insert_request(connection)
        insert_event(connection)
        insert_outbox(connection)
