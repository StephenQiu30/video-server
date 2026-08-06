-- Universal video downloader: current PostgreSQL schema.
-- This file initializes a new database. The project intentionally carries no
-- migration history or compatibility upgrade path.

BEGIN;

CREATE TABLE media_inspections (
    id UUID PRIMARY KEY,
    owner_hash VARCHAR(64) NOT NULL,
    idempotency_key VARCHAR(128) NOT NULL,
    request_fingerprint VARCHAR(64) NOT NULL,
    url_ciphertext BYTEA NOT NULL,
    url_nonce BYTEA NOT NULL,
    url_key_id VARCHAR(64) NOT NULL,
    extractor_key VARCHAR(128) NOT NULL,
    provider_media_id VARCHAR(256) NOT NULL,
    title TEXT NOT NULL,
    duration_seconds INTEGER NOT NULL,
    metadata JSONB NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_media_inspections_owner_idempotency
        UNIQUE (owner_hash, idempotency_key),
    CONSTRAINT ck_inspection_duration CHECK (duration_seconds > 0)
);

CREATE INDEX ix_media_inspections_owner_expires
    ON media_inspections (owner_hash, expires_at);

CREATE TABLE media_formats (
    id UUID PRIMARY KEY,
    inspection_id UUID NOT NULL
        REFERENCES media_inspections (id) ON DELETE CASCADE,
    display_name VARCHAR(128) NOT NULL,
    plan_fingerprint VARCHAR(64) NOT NULL,
    semantic_plan JSONB NOT NULL,
    provider_hints JSONB NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_media_formats_inspection_plan
        UNIQUE (inspection_id, plan_fingerprint)
);

CREATE INDEX ix_media_formats_inspection ON media_formats (inspection_id);
CREATE INDEX ix_media_formats_expires ON media_formats (expires_at);

CREATE TABLE download_jobs (
    id UUID PRIMARY KEY,
    inspection_id UUID NOT NULL REFERENCES media_inspections (id),
    format_id UUID NOT NULL REFERENCES media_formats (id),
    owner_hash VARCHAR(64) NOT NULL,
    idempotency_key VARCHAR(128) NOT NULL,
    request_fingerprint VARCHAR(64) NOT NULL,
    semantic_plan JSONB NOT NULL,
    status VARCHAR(24) NOT NULL DEFAULT 'queued',
    stage VARCHAR(24),
    stage_rank INTEGER NOT NULL DEFAULT 0,
    progress INTEGER NOT NULL DEFAULT 0,
    attempt INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 3,
    version INTEGER NOT NULL DEFAULT 0,
    lease_owner VARCHAR(128),
    lease_expires_at TIMESTAMPTZ,
    heartbeat_at TIMESTAMPTZ,
    started_at TIMESTAMPTZ,
    retry_at TIMESTAMPTZ,
    cancel_requested_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    error_code VARCHAR(64),
    error_message VARCHAR(512),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_download_jobs_owner_idempotency
        UNIQUE (owner_hash, idempotency_key),
    CONSTRAINT ck_download_jobs_status CHECK (
        status IN ('queued', 'running', 'retry_wait', 'succeeded', 'failed', 'cancelled')
    ),
    CONSTRAINT ck_download_jobs_progress CHECK (progress BETWEEN 0 AND 100),
    CONSTRAINT ck_download_jobs_attempt CHECK (attempt >= 0),
    CONSTRAINT ck_download_jobs_max_attempts CHECK (max_attempts > 0),
    CONSTRAINT ck_download_jobs_version CHECK (version >= 0),
    CONSTRAINT ck_download_jobs_stage_rank CHECK (stage_rank BETWEEN 0 AND 5)
);

CREATE INDEX ix_download_jobs_owner_created
    ON download_jobs (owner_hash, created_at);
CREATE INDEX ix_download_jobs_claim ON download_jobs (status, retry_at);
CREATE INDEX ix_download_jobs_stale ON download_jobs (status, lease_expires_at);

CREATE TABLE artifacts (
    id UUID PRIMARY KEY,
    job_id UUID NOT NULL REFERENCES download_jobs (id) ON DELETE CASCADE,
    attempt INTEGER NOT NULL,
    bucket VARCHAR(128) NOT NULL,
    object_key TEXT NOT NULL,
    sha256 VARCHAR(64) NOT NULL,
    size_bytes BIGINT NOT NULL,
    duration_ms INTEGER NOT NULL,
    container VARCHAR(16) NOT NULL,
    content_type VARCHAR(128) NOT NULL,
    media_metadata JSONB NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    deleted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_artifacts_job UNIQUE (job_id),
    CONSTRAINT uq_artifacts_object UNIQUE (bucket, object_key),
    CONSTRAINT ck_artifacts_attempt CHECK (attempt > 0),
    CONSTRAINT ck_artifacts_size CHECK (size_bytes > 0),
    CONSTRAINT ck_artifacts_duration CHECK (duration_ms > 0),
    CONSTRAINT ck_artifacts_sha256_length CHECK (length(sha256) = 64)
);

CREATE INDEX ix_artifacts_expires ON artifacts (expires_at);

CREATE TABLE analysis_jobs (
    id UUID PRIMARY KEY,
    artifact_id UUID NOT NULL,
    owner_hash VARCHAR(64) NOT NULL,
    idempotency_key VARCHAR(128) NOT NULL,
    request_fingerprint VARCHAR(64) NOT NULL,
    input_sha256 VARCHAR(64) NOT NULL,
    profile VARCHAR(128) NOT NULL,
    schema_version VARCHAR(128) NOT NULL,
    output_language VARCHAR(35) NOT NULL,
    status VARCHAR(24) NOT NULL DEFAULT 'queued',
    stage VARCHAR(24),
    stage_rank INTEGER NOT NULL DEFAULT 0,
    progress INTEGER NOT NULL DEFAULT 0,
    attempt INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 3,
    version INTEGER NOT NULL DEFAULT 0,
    lease_owner VARCHAR(128),
    lease_expires_at TIMESTAMPTZ,
    heartbeat_at TIMESTAMPTZ,
    started_at TIMESTAMPTZ,
    retry_at TIMESTAMPTZ,
    cancel_requested_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    error_code VARCHAR(64),
    error_message VARCHAR(512),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_analysis_jobs_owner_idempotency
        UNIQUE (owner_hash, idempotency_key),
    CONSTRAINT ck_analysis_jobs_status CHECK (
        status IN ('queued', 'running', 'retry_wait', 'succeeded', 'failed', 'cancelled')
    ),
    CONSTRAINT ck_analysis_jobs_progress CHECK (progress BETWEEN 0 AND 100),
    CONSTRAINT ck_analysis_jobs_attempt CHECK (attempt >= 0),
    CONSTRAINT ck_analysis_jobs_max_attempts CHECK (max_attempts > 0),
    CONSTRAINT ck_analysis_jobs_version CHECK (version >= 0),
    CONSTRAINT ck_analysis_jobs_stage_rank CHECK (stage_rank BETWEEN 0 AND 4),
    CONSTRAINT ck_analysis_jobs_sha256_length CHECK (length(input_sha256) = 64)
);

CREATE INDEX ix_analysis_jobs_owner_created
    ON analysis_jobs (owner_hash, created_at);
CREATE INDEX ix_analysis_jobs_claim ON analysis_jobs (status, retry_at);
CREATE INDEX ix_analysis_jobs_stale ON analysis_jobs (status, lease_expires_at);
CREATE INDEX ix_analysis_jobs_artifact ON analysis_jobs (artifact_id);

CREATE TABLE analysis_results (
    id UUID PRIMARY KEY,
    job_id UUID NOT NULL REFERENCES analysis_jobs (id) ON DELETE CASCADE,
    input_sha256 VARCHAR(64) NOT NULL,
    schema_version VARCHAR(128) NOT NULL,
    language VARCHAR(35) NOT NULL,
    result_json JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_analysis_results_job UNIQUE (job_id),
    CONSTRAINT ck_analysis_results_sha256_length CHECK (length(input_sha256) = 64),
    CONSTRAINT ck_analysis_results_json_object CHECK (jsonb_typeof(result_json) = 'object')
);

CREATE TABLE analysis_artifact_locks (
    job_id UUID PRIMARY KEY
        REFERENCES analysis_jobs (id) ON DELETE CASCADE,
    artifact_id UUID NOT NULL
        REFERENCES artifacts (id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX ix_analysis_artifact_locks_artifact
    ON analysis_artifact_locks (artifact_id);

CREATE TABLE outbox_events (
    id UUID PRIMARY KEY,
    aggregate_type VARCHAR(64) NOT NULL,
    aggregate_id UUID NOT NULL,
    event_type VARCHAR(128) NOT NULL,
    payload JSONB NOT NULL,
    available_at TIMESTAMPTZ NOT NULL,
    published_at TIMESTAMPTZ,
    publish_attempts INTEGER NOT NULL DEFAULT 0,
    last_attempt_at TIMESTAMPTZ,
    next_attempt_at TIMESTAMPTZ,
    last_error TEXT,
    lock_owner VARCHAR(128),
    lock_expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_outbox_publish_attempts CHECK (publish_attempts >= 0)
);

CREATE INDEX ix_outbox_events_publishable
    ON outbox_events (published_at, available_at, next_attempt_at);
CREATE INDEX ix_outbox_events_lock ON outbox_events (lock_expires_at);

COMMIT;
