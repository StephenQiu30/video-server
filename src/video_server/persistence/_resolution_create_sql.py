"""Frozen SQL statements for atomic source-resolution creation."""

from __future__ import annotations

from sqlalchemy import text

SELECT_EXISTING = text(
    """
    SELECT id, job_id, request_digest, created_at
    FROM source_resolution_requests
    WHERE owner_id = :owner_id
      AND operation = 'probe'
      AND idempotency_key_digest = :idempotency_key_digest
    FOR UPDATE
    """
)

SELECT_CURRENT_RIGHTS = text(
    """
    SELECT version, locale, statement_sha256
    FROM rights_statement_catalog
    WHERE locale = :rights_statement_locale
      AND effective_at <= :created_at
      AND (expires_at IS NULL OR :created_at < expires_at)
      AND (superseded_at IS NULL OR :created_at < superseded_at)
    FOR SHARE
    """
)

INSERT_JOB = text(
    """
    INSERT INTO jobs (
        id, owner_id, job_type, status, stage, attempt, progress,
        created_at, updated_at, terminal_at,
        detail_eligible_at, detail_must_purge_by
    ) VALUES (
        :job_id, :owner_id, 'SOURCE_RESOLUTION', 'QUEUED',
        'VALIDATING_URL', 0, NULL, :created_at, :created_at, NULL,
        :detail_eligible_at, :detail_must_purge_by
    )
    """
)

INSERT_REQUEST = text(
    """
    INSERT INTO source_resolution_requests (
        id, owner_id, operation, job_id,
        idempotency_key_digest, request_digest,
        url_ciphertext, url_nonce, url_wrapped_dek, url_wrap_nonce, url_key_id,
        rights_statement_version, rights_statement_locale,
        rights_statement_sha256, rights_confirmed_at, created_at,
        detail_eligible_at, detail_must_purge_by
    ) VALUES (
        :resolution_id, :owner_id, 'probe', :job_id,
        :idempotency_key_digest, :request_digest,
        :url_ciphertext, :url_nonce, :url_wrapped_dek, :url_wrap_nonce, :url_key_id,
        :rights_statement_version, :rights_statement_locale,
        :rights_statement_sha256, :created_at, :created_at,
        :detail_eligible_at, :detail_must_purge_by
    )
    """
)

INSERT_EVENT = text(
    """
    INSERT INTO job_events (
        job_id, owner_id, aggregate_created_at,
        status, stage, attempt, progress, occurred_at,
        detail_eligible_at, detail_must_purge_by
    ) VALUES (
        :job_id, :owner_id, :created_at,
        'QUEUED', 'VALIDATING_URL', 0, NULL, :created_at,
        :detail_eligible_at, :detail_must_purge_by
    )
    """
)

INSERT_OUTBOX = text(
    """
    INSERT INTO outbox_messages (
        resolution_request_id, job_id, owner_id, aggregate_created_at, kind,
        attempts, lease_version, retention_eligible_at, retention_must_purge_by
    ) VALUES (
        :resolution_id, :job_id, :owner_id, :created_at,
        'SOURCE_RESOLUTION_REQUESTED', 0, 0,
        :detail_eligible_at, :detail_must_purge_by
    )
    """
)
