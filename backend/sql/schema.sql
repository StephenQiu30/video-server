-- Universal video downloader: current PostgreSQL schema.
-- The Docker database-init service applies this file on every Compose startup.
-- Keep creation idempotent so both empty and already initialized volumes converge
-- on all currently required tables and indexes. This remains a current-state
-- schema, not a historical migration chain.

BEGIN;

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY,
    username VARCHAR(32) NOT NULL,
    normalized_username VARCHAR(64) NOT NULL,
    email VARCHAR(320) NOT NULL,
    password_hash VARCHAR(512) NOT NULL,
    role VARCHAR(16) NOT NULL DEFAULT 'user',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_users_email UNIQUE (email),
    CONSTRAINT uq_users_normalized_username UNIQUE (normalized_username),
    CONSTRAINT ck_users_role CHECK (role IN ('admin', 'user'))
);

CREATE TABLE IF NOT EXISTS auth_sessions (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    token_hash VARCHAR(64) NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_auth_sessions_token_hash UNIQUE (token_hash)
);

CREATE INDEX IF NOT EXISTS ix_auth_sessions_user ON auth_sessions (user_id);
CREATE INDEX IF NOT EXISTS ix_auth_sessions_expires ON auth_sessions (expires_at);

CREATE TABLE IF NOT EXISTS provider_catalog_entries (
    key VARCHAR(32) PRIMARY KEY,
    display_name VARCHAR(64) NOT NULL,
    sort_order INTEGER NOT NULL,
    is_visible BOOLEAN NOT NULL DEFAULT TRUE,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_provider_catalog_sort_order CHECK (
        sort_order BETWEEN 0 AND 10000
    )
);

INSERT INTO provider_catalog_entries (
    key, display_name, sort_order, is_visible, is_deleted
) VALUES
    ('youtube', 'YouTube', 10, TRUE, FALSE),
    ('bilibili', '哔哩哔哩', 20, TRUE, FALSE),
    ('douyin', '抖音', 30, TRUE, FALSE),
    ('tiktok', 'TikTok', 40, TRUE, FALSE),
    ('xiaohongshu', '小红书', 50, TRUE, FALSE),
    ('kuaishou', '快手', 60, TRUE, FALSE),
    ('vimeo', 'Vimeo', 70, TRUE, FALSE),
    ('x', 'X / Twitter', 80, TRUE, FALSE),
    ('instagram', 'Instagram', 90, TRUE, FALSE),
    ('facebook', 'Facebook', 100, TRUE, FALSE),
    ('twitch', 'Twitch', 110, TRUE, FALSE),
    ('reddit', 'Reddit', 120, TRUE, FALSE),
    ('pinterest', 'Pinterest', 130, TRUE, FALSE),
    ('weibo', '微博', 140, TRUE, FALSE),
    ('youku', '优酷', 150, TRUE, FALSE),
    ('qqvideo', '腾讯视频', 160, TRUE, FALSE),
    ('wechat_channels', '微信视频号', 170, TRUE, FALSE)
ON CONFLICT (key) DO NOTHING;

CREATE TABLE IF NOT EXISTS media_inspections (
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

CREATE INDEX IF NOT EXISTS ix_media_inspections_owner_expires
    ON media_inspections (owner_hash, expires_at);

CREATE TABLE IF NOT EXISTS media_formats (
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

CREATE INDEX IF NOT EXISTS ix_media_formats_inspection ON media_formats (inspection_id);
CREATE INDEX IF NOT EXISTS ix_media_formats_expires ON media_formats (expires_at);

CREATE TABLE IF NOT EXISTS download_jobs (
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

CREATE INDEX IF NOT EXISTS ix_download_jobs_owner_created
    ON download_jobs (owner_hash, created_at);
CREATE INDEX IF NOT EXISTS ix_download_jobs_created ON download_jobs (created_at);
CREATE INDEX IF NOT EXISTS ix_download_jobs_claim ON download_jobs (status, retry_at);
CREATE INDEX IF NOT EXISTS ix_download_jobs_stale ON download_jobs (status, lease_expires_at);
CREATE INDEX IF NOT EXISTS ix_download_jobs_queued_recovery ON download_jobs (status, updated_at);

CREATE TABLE IF NOT EXISTS artifacts (
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

CREATE INDEX IF NOT EXISTS ix_artifacts_expires ON artifacts (expires_at);

CREATE TABLE IF NOT EXISTS analysis_jobs (
    id UUID PRIMARY KEY,
    artifact_id UUID NOT NULL,
    owner_hash VARCHAR(64) NOT NULL,
    idempotency_key VARCHAR(128) NOT NULL,
    request_fingerprint VARCHAR(64) NOT NULL,
    input_sha256 VARCHAR(64) NOT NULL,
    skill_id VARCHAR(128) NOT NULL,
    skill_instructions TEXT NOT NULL,
    output_language VARCHAR(35) NOT NULL,
    custom_prompt TEXT,
    status VARCHAR(24) NOT NULL DEFAULT 'queued',
    stage VARCHAR(24),
    stage_rank INTEGER NOT NULL DEFAULT 0,
    progress INTEGER NOT NULL DEFAULT 0,
    attempt INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 3,
    version INTEGER NOT NULL DEFAULT 0,
    active_run_id UUID,
    current_run_no INTEGER NOT NULL DEFAULT 1,
    current_run_trigger VARCHAR(24) NOT NULL DEFAULT 'initial',
    current_report_id UUID,
    lease_owner VARCHAR(128),
    lease_expires_at TIMESTAMPTZ,
    heartbeat_at TIMESTAMPTZ,
    started_at TIMESTAMPTZ,
    retry_at TIMESTAMPTZ,
    cancel_requested_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    error_code VARCHAR(64),
    error_message VARCHAR(512),
    deleted_at TIMESTAMPTZ,
    retry_available_until TIMESTAMPTZ,
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
    CONSTRAINT ck_analysis_jobs_run_no CHECK (current_run_no > 0),
    CONSTRAINT ck_analysis_jobs_stage_rank CHECK (stage_rank BETWEEN 0 AND 4),
    CONSTRAINT ck_analysis_jobs_sha256_length CHECK (length(input_sha256) = 64)
);

CREATE INDEX IF NOT EXISTS ix_analysis_jobs_owner_created
    ON analysis_jobs (owner_hash, created_at);
CREATE INDEX IF NOT EXISTS ix_analysis_jobs_claim ON analysis_jobs (status, retry_at);
CREATE INDEX IF NOT EXISTS ix_analysis_jobs_stale ON analysis_jobs (status, lease_expires_at);
CREATE INDEX IF NOT EXISTS ix_analysis_jobs_queued_recovery
    ON analysis_jobs (status, updated_at);
CREATE INDEX IF NOT EXISTS ix_analysis_jobs_artifact ON analysis_jobs (artifact_id);

ALTER TABLE analysis_jobs ADD COLUMN IF NOT EXISTS active_run_id UUID;
ALTER TABLE analysis_jobs ADD COLUMN IF NOT EXISTS current_run_no INTEGER NOT NULL DEFAULT 1;
ALTER TABLE analysis_jobs ADD COLUMN IF NOT EXISTS current_run_trigger VARCHAR(24) NOT NULL DEFAULT 'initial';
ALTER TABLE analysis_jobs ADD COLUMN IF NOT EXISTS current_report_id UUID;
ALTER TABLE analysis_jobs ADD COLUMN IF NOT EXISTS skill_id VARCHAR(128);
ALTER TABLE analysis_jobs ADD COLUMN IF NOT EXISTS skill_instructions TEXT;
ALTER TABLE analysis_jobs ADD COLUMN IF NOT EXISTS custom_prompt TEXT;
ALTER TABLE analysis_jobs ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;
ALTER TABLE analysis_jobs ADD COLUMN IF NOT EXISTS retry_available_until TIMESTAMPTZ;
UPDATE analysis_jobs AS analysis
SET retry_available_until = artifact.expires_at
FROM artifacts AS artifact
WHERE artifact.id = analysis.artifact_id
  AND analysis.retry_available_until IS NULL;
UPDATE analysis_jobs SET
    skill_id = COALESCE(skill_id, 'director-breakdown'),
    skill_instructions = COALESCE(
        skill_instructions,
        '对完整视频执行连续分镜、高光与视觉资产分析。'
    )
WHERE skill_id IS NULL OR skill_instructions IS NULL;
ALTER TABLE analysis_jobs ALTER COLUMN skill_id SET NOT NULL;
ALTER TABLE analysis_jobs ALTER COLUMN skill_instructions SET NOT NULL;
ALTER TABLE analysis_jobs DROP COLUMN IF EXISTS profile;
ALTER TABLE analysis_jobs DROP COLUMN IF EXISTS schema_version;
ALTER TABLE analysis_jobs DROP CONSTRAINT IF EXISTS ck_analysis_jobs_stage_rank;
ALTER TABLE analysis_jobs ADD CONSTRAINT ck_analysis_jobs_stage_rank
    CHECK (stage_rank BETWEEN 0 AND 4);

CREATE TABLE IF NOT EXISTS analysis_runs (
    id UUID PRIMARY KEY,
    job_id UUID NOT NULL REFERENCES analysis_jobs (id) ON DELETE CASCADE,
    run_no INTEGER NOT NULL,
    trigger VARCHAR(24) NOT NULL,
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
    provider VARCHAR(32),
    model VARCHAR(128),
    cli_version VARCHAR(128),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_analysis_runs_job_no UNIQUE (job_id, run_no),
    CONSTRAINT ck_analysis_runs_trigger CHECK (
        trigger IN ('initial', 'manual_retry', 'manual_rerun')
    ),
    CONSTRAINT ck_analysis_runs_status CHECK (
        status IN ('queued', 'running', 'retry_wait', 'succeeded', 'failed', 'cancelled')
    ),
    CONSTRAINT ck_analysis_runs_progress CHECK (progress BETWEEN 0 AND 100),
    CONSTRAINT ck_analysis_runs_attempt CHECK (attempt >= 0),
    CONSTRAINT ck_analysis_runs_max_attempts CHECK (max_attempts > 0),
    CONSTRAINT ck_analysis_runs_version CHECK (version >= 0),
    CONSTRAINT ck_analysis_runs_stage_rank CHECK (stage_rank BETWEEN 0 AND 4)
);

CREATE INDEX IF NOT EXISTS ix_analysis_runs_job_created
    ON analysis_runs (job_id, created_at);
CREATE INDEX IF NOT EXISTS ix_analysis_runs_claim ON analysis_runs (status, retry_at);
CREATE INDEX IF NOT EXISTS ix_analysis_runs_stale ON analysis_runs (status, lease_expires_at);

ALTER TABLE analysis_runs DROP CONSTRAINT IF EXISTS ck_analysis_runs_stage_rank;
ALTER TABLE analysis_runs ADD CONSTRAINT ck_analysis_runs_stage_rank
    CHECK (stage_rank BETWEEN 0 AND 4);

INSERT INTO analysis_runs (
    id, job_id, run_no, trigger, status, stage, stage_rank, progress,
    attempt, max_attempts, version, lease_owner, lease_expires_at,
    heartbeat_at, started_at, retry_at, cancel_requested_at, finished_at,
    error_code, error_message, created_at, updated_at
)
SELECT
    id, id, 1, 'initial', status, stage, stage_rank, progress,
    attempt, max_attempts, version, lease_owner, lease_expires_at,
    heartbeat_at, started_at, retry_at, cancel_requested_at, finished_at,
    error_code, error_message, created_at, updated_at
FROM analysis_jobs
ON CONFLICT (job_id, run_no) DO NOTHING;

UPDATE analysis_jobs SET active_run_id = id WHERE active_run_id IS NULL;
ALTER TABLE analysis_jobs ALTER COLUMN active_run_id SET NOT NULL;

CREATE TABLE IF NOT EXISTS analysis_retry_operations (
    id UUID PRIMARY KEY,
    job_id UUID NOT NULL REFERENCES analysis_jobs (id) ON DELETE CASCADE,
    run_id UUID NOT NULL REFERENCES analysis_runs (id) ON DELETE CASCADE,
    operation VARCHAR(32) NOT NULL,
    idempotency_key VARCHAR(128) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_analysis_retry_operations_key
        UNIQUE (job_id, operation, idempotency_key)
);

CREATE TABLE IF NOT EXISTS analysis_report_versions (
    id UUID PRIMARY KEY,
    job_id UUID NOT NULL REFERENCES analysis_jobs (id) ON DELETE CASCADE,
    run_id UUID NOT NULL REFERENCES analysis_runs (id) ON DELETE CASCADE,
    input_sha256 VARCHAR(64) NOT NULL,
    language VARCHAR(35) NOT NULL,
    result_json JSONB NOT NULL,
    report_markdown TEXT NOT NULL,
    content_sha256 VARCHAR(64) NOT NULL,
    renderer_version VARCHAR(64) NOT NULL,
    provider VARCHAR(32) NOT NULL,
    model VARCHAR(128) NOT NULL,
    cli_version VARCHAR(128) NOT NULL,
    status VARCHAR(24) NOT NULL DEFAULT 'validated',
    attempt INTEGER NOT NULL DEFAULT 0,
    lease_owner VARCHAR(128),
    lease_expires_at TIMESTAMPTZ,
    error_message VARCHAR(512),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    published_at TIMESTAMPTZ,
    CONSTRAINT uq_analysis_report_versions_run UNIQUE (run_id),
    CONSTRAINT ck_analysis_report_versions_status CHECK (
        status IN (
            'validated', 'publishing', 'available', 'publish_failed',
            'delete_pending', 'deleted'
        )
    ),
    CONSTRAINT ck_analysis_report_versions_input_sha CHECK (length(input_sha256) = 64),
    CONSTRAINT ck_analysis_report_versions_content_sha CHECK (length(content_sha256) = 64),
    CONSTRAINT ck_analysis_report_versions_attempt CHECK (attempt >= 0),
    CONSTRAINT ck_analysis_report_versions_json_object CHECK (jsonb_typeof(result_json) = 'object')
);

CREATE TABLE IF NOT EXISTS analysis_report_artifacts (
    id UUID PRIMARY KEY,
    report_id UUID NOT NULL REFERENCES analysis_report_versions (id) ON DELETE CASCADE,
    format VARCHAR(16) NOT NULL,
    bucket VARCHAR(128) NOT NULL,
    object_key VARCHAR(512) NOT NULL,
    content_type VARCHAR(128) NOT NULL,
    size_bytes INTEGER NOT NULL,
    sha256 VARCHAR(64) NOT NULL,
    status VARCHAR(24) NOT NULL DEFAULT 'available',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    available_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP + INTERVAL '1 day'),
    deleted_at TIMESTAMPTZ,
    CONSTRAINT uq_analysis_report_artifacts_format UNIQUE (report_id, format),
    CONSTRAINT uq_analysis_report_artifacts_object UNIQUE (bucket, object_key),
    CONSTRAINT ck_analysis_report_artifacts_format CHECK (format IN ('markdown', 'docx')),
    CONSTRAINT ck_analysis_report_artifacts_status CHECK (
        status IN ('available', 'delete_pending', 'deleted', 'failed')
    ),
    CONSTRAINT ck_analysis_report_artifacts_size CHECK (size_bytes > 0),
    CONSTRAINT ck_analysis_report_artifacts_sha CHECK (length(sha256) = 64)
);

ALTER TABLE analysis_report_versions
    DROP CONSTRAINT IF EXISTS ck_analysis_report_versions_status;
ALTER TABLE analysis_report_versions
    ADD CONSTRAINT ck_analysis_report_versions_status CHECK (
        status IN (
            'validated', 'publishing', 'available', 'publish_failed',
            'delete_pending', 'deleted'
        )
    );
ALTER TABLE analysis_report_artifacts
    ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ;
UPDATE analysis_report_artifacts
SET expires_at = created_at + INTERVAL '1 day'
WHERE expires_at IS NULL;
ALTER TABLE analysis_report_artifacts ALTER COLUMN expires_at SET NOT NULL;

-- Legacy releases could mark a job succeeded before the durable Markdown and
-- DOCX report existed. Fail those inconsistent projections closed so clients
-- can retry instead of receiving a false success without downloadable output.
UPDATE analysis_jobs
SET
    status = 'failed',
    stage = NULL,
    stage_rank = 0,
    version = version + 1,
    error_code = 'analysis_report_unavailable',
    error_message = 'durable analysis report is unavailable',
    finished_at = COALESCE(finished_at, CURRENT_TIMESTAMP),
    updated_at = CURRENT_TIMESTAMP
WHERE status = 'succeeded' AND current_report_id IS NULL;

UPDATE analysis_runs AS run
SET
    status = analysis.status,
    stage = analysis.stage,
    stage_rank = analysis.stage_rank,
    progress = analysis.progress,
    attempt = analysis.attempt,
    max_attempts = analysis.max_attempts,
    version = analysis.version,
    finished_at = analysis.finished_at,
    error_code = analysis.error_code,
    error_message = analysis.error_message,
    updated_at = analysis.updated_at
FROM analysis_jobs AS analysis
WHERE run.id = analysis.active_run_id
  AND run.status = 'succeeded'
  AND analysis.status = 'failed'
  AND analysis.error_code = 'analysis_report_unavailable';

ALTER TABLE analysis_jobs
    DROP CONSTRAINT IF EXISTS ck_analysis_jobs_succeeded_report;
ALTER TABLE analysis_jobs
    ADD CONSTRAINT ck_analysis_jobs_succeeded_report CHECK (
        status <> 'succeeded' OR current_report_id IS NOT NULL
    );

CREATE TABLE IF NOT EXISTS analysis_artifact_locks (
    job_id UUID PRIMARY KEY
        REFERENCES analysis_jobs (id) ON DELETE CASCADE,
    artifact_id UUID NOT NULL
        REFERENCES artifacts (id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_analysis_artifact_locks_artifact
    ON analysis_artifact_locks (artifact_id);

CREATE TABLE IF NOT EXISTS analysis_worker_heartbeats (
    worker_id VARCHAR(128) PRIMARY KEY,
    app_version VARCHAR(128) NOT NULL,
    message_schema_version INTEGER NOT NULL,
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_analysis_worker_heartbeats_schema_version CHECK (
        message_schema_version > 0
    )
);

CREATE INDEX IF NOT EXISTS ix_analysis_worker_heartbeats_last_seen
    ON analysis_worker_heartbeats (last_seen_at);

CREATE TABLE IF NOT EXISTS outbox_events (
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

CREATE INDEX IF NOT EXISTS ix_outbox_events_publishable
    ON outbox_events (published_at, available_at, next_attempt_at);
CREATE INDEX IF NOT EXISTS ix_outbox_events_lock ON outbox_events (lock_expires_at);

CREATE TABLE IF NOT EXISTS rabbitmq_dlq_replays (
    id UUID PRIMARY KEY,
    source_queue VARCHAR(64) NOT NULL,
    original_event_id UUID NOT NULL,
    replay_event_id UUID NOT NULL UNIQUE,
    replay_count INTEGER NOT NULL,
    actor VARCHAR(128) NOT NULL,
    reason VARCHAR(256) NOT NULL,
    status VARCHAR(24) NOT NULL,
    error_code VARCHAR(128),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ,
    CONSTRAINT uq_rabbitmq_dlq_replay_attempt
        UNIQUE (source_queue, original_event_id, replay_count),
    CONSTRAINT ck_rabbitmq_dlq_replay_queue CHECK (
        source_queue IN (
            'video.download.dead',
            'video.analysis.dead',
            'video.analysis-report.dead'
        )
    ),
    CONSTRAINT ck_rabbitmq_dlq_replay_status CHECK (
        status IN ('pending', 'published', 'failed')
    ),
    CONSTRAINT ck_rabbitmq_dlq_replay_count CHECK (replay_count BETWEEN 1 AND 3)
);

CREATE TABLE IF NOT EXISTS operational_counters (
    metric VARCHAR(64) NOT NULL,
    dimension VARCHAR(64) NOT NULL,
    value BIGINT NOT NULL DEFAULT 0,
    PRIMARY KEY (metric, dimension),
    CONSTRAINT ck_operational_counters_value CHECK (value >= 0)
);

CREATE TABLE IF NOT EXISTS provider_canary_results (
    id UUID PRIMARY KEY,
    target_id VARCHAR(128) NOT NULL,
    provider_key VARCHAR(32) NOT NULL,
    profile_version VARCHAR(128) NOT NULL,
    stage VARCHAR(16) NOT NULL,
    access_mode VARCHAR(24) NOT NULL,
    outcome VARCHAR(16) NOT NULL,
    stable_error_code VARCHAR(128),
    checked_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    duration_ms INTEGER NOT NULL,
    engine_commit VARCHAR(128) NOT NULL,
    egress_affinity_id VARCHAR(128) NOT NULL,
    client_profile_id VARCHAR(128) NOT NULL,
    CONSTRAINT ck_provider_canary_stage CHECK (
        stage IN ('metadata', 'media', 'analysis')
    ),
    CONSTRAINT ck_provider_canary_access_mode CHECK (
        access_mode IN ('anonymous', 'operator_managed')
    ),
    CONSTRAINT ck_provider_canary_outcome CHECK (
        outcome IN ('succeeded', 'failed')
    ),
    CONSTRAINT ck_provider_canary_duration CHECK (duration_ms >= 0),
    CONSTRAINT ck_provider_canary_error CHECK (
        (outcome = 'failed') = (stable_error_code IS NOT NULL)
    )
);

ALTER TABLE provider_canary_results
    DROP CONSTRAINT IF EXISTS ck_provider_canary_stage;
ALTER TABLE provider_canary_results
    ADD CONSTRAINT ck_provider_canary_stage CHECK (
        stage IN ('metadata', 'media', 'analysis')
    );

CREATE INDEX IF NOT EXISTS ix_provider_canary_provider_checked
    ON provider_canary_results (provider_key, checked_at);
CREATE INDEX IF NOT EXISTS ix_provider_canary_target_checked
    ON provider_canary_results (target_id, stage, checked_at);

CREATE TABLE IF NOT EXISTS task_events (
    id UUID PRIMARY KEY,
    owner_hash VARCHAR(64) NOT NULL,
    task_type VARCHAR(16) NOT NULL,
    task_id UUID NOT NULL,
    run_id UUID,
    run_no INTEGER,
    version INTEGER NOT NULL,
    event_type VARCHAR(64) NOT NULL,
    payload JSONB NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_task_events_version UNIQUE (task_type, task_id, version),
    CONSTRAINT ck_task_events_type CHECK (task_type IN ('download', 'analysis')),
    CONSTRAINT ck_task_events_version CHECK (version >= 0),
    CONSTRAINT ck_task_events_payload_object CHECK (jsonb_typeof(payload) = 'object')
);

CREATE INDEX IF NOT EXISTS ix_task_events_owner_task
    ON task_events (owner_hash, task_type, task_id, version);
CREATE INDEX IF NOT EXISTS ix_task_events_occurred ON task_events (occurred_at);

CREATE OR REPLACE FUNCTION emit_download_task_event() RETURNS trigger AS $$
DECLARE
    event_uuid UUID := gen_random_uuid();
    public_payload JSONB;
BEGIN
    public_payload := jsonb_strip_nulls(jsonb_build_object(
        'task_type', 'download', 'task_id', NEW.id::text,
        'version', NEW.version, 'status', NEW.status, 'stage', NEW.stage,
        'progress', NEW.progress, 'attempt', NEW.attempt,
        'error', CASE WHEN NEW.error_code IS NULL THEN NULL
            ELSE jsonb_build_object('code', NEW.error_code) END,
        'occurred_at', NEW.updated_at
    ));
    INSERT INTO task_events (
        id, owner_hash, task_type, task_id, version, event_type, payload, occurred_at
    ) VALUES (
        event_uuid, NEW.owner_hash, 'download', NEW.id, NEW.version,
        'task.updated', public_payload, NEW.updated_at
    );
    INSERT INTO outbox_events (
        id, aggregate_type, aggregate_id, event_type, payload, available_at, created_at
    ) VALUES (
        event_uuid, 'task', NEW.id, 'task.state.changed', public_payload,
        NEW.updated_at, NEW.updated_at
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION emit_analysis_task_event() RETURNS trigger AS $$
DECLARE
    event_uuid UUID := gen_random_uuid();
    report_state VARCHAR(24);
    public_payload JSONB;
BEGIN
    SELECT status INTO report_state FROM analysis_report_versions
        WHERE job_id = NEW.id ORDER BY created_at DESC LIMIT 1;
    public_payload := jsonb_strip_nulls(jsonb_build_object(
        'task_type', 'analysis', 'task_id', NEW.id::text,
        'run_id', NEW.active_run_id::text, 'run_no', NEW.current_run_no,
        'version', NEW.version, 'status', NEW.status, 'stage', NEW.stage,
        'progress', NEW.progress, 'attempt', NEW.attempt,
        'report_status', report_state,
        'error', CASE WHEN NEW.error_code IS NULL THEN NULL
            ELSE jsonb_build_object('code', NEW.error_code) END,
        'occurred_at', NEW.updated_at
    ));
    INSERT INTO task_events (
        id, owner_hash, task_type, task_id, run_id, run_no, version,
        event_type, payload, occurred_at
    ) VALUES (
        event_uuid, NEW.owner_hash, 'analysis', NEW.id, NEW.active_run_id,
        NEW.current_run_no, NEW.version, 'task.updated', public_payload, NEW.updated_at
    );
    INSERT INTO outbox_events (
        id, aggregate_type, aggregate_id, event_type, payload, available_at, created_at
    ) VALUES (
        event_uuid, 'task', NEW.id, 'task.state.changed', public_payload,
        NEW.updated_at, NEW.updated_at
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS download_task_event_trigger ON download_jobs;
CREATE TRIGGER download_task_event_trigger
AFTER INSERT OR UPDATE OF version ON download_jobs
FOR EACH ROW EXECUTE FUNCTION emit_download_task_event();

DROP TRIGGER IF EXISTS analysis_task_event_trigger ON analysis_jobs;
CREATE TRIGGER analysis_task_event_trigger
AFTER INSERT OR UPDATE OF version ON analysis_jobs
FOR EACH ROW EXECUTE FUNCTION emit_analysis_task_event();

COMMIT;
