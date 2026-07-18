"""Frozen revision-0002 transition guards for resolution Jobs."""

from __future__ import annotations

from alembic import op


def create_job_guards() -> None:
    op.execute(
        """
        CREATE FUNCTION guard_jobs_initial_state()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF NEW.status <> 'QUEUED'
                OR NEW.stage <> 'VALIDATING_URL'
                OR NEW.attempt <> 0
                OR NEW.progress IS NOT NULL
                OR NEW.created_at IS DISTINCT FROM NEW.updated_at
                OR NEW.terminal_at IS NOT NULL
                OR NEW.error_code IS NOT NULL
                OR NEW.error_title IS NOT NULL
                OR NEW.error_detail IS NOT NULL
                OR NEW.error_retryable IS NOT NULL
                OR NEW.error_correlation_id IS NOT NULL
                OR NEW.error_field IS NOT NULL
                OR NEW.error_policy IS NOT NULL
                OR NEW.error_actions IS NOT NULL
                OR NEW.error_retry_after_seconds IS NOT NULL
            THEN
                RAISE EXCEPTION 'jobs must start in the exact queued state'
                    USING ERRCODE = '23514', CONSTRAINT = 'ck_jobs_initial_state';
            END IF;
            RETURN NEW;
        END;
        $$;

        CREATE TRIGGER tr_jobs_initial_state
        BEFORE INSERT ON jobs
        FOR EACH ROW EXECUTE FUNCTION guard_jobs_initial_state();
        """
    )
    op.execute(
        """
        CREATE FUNCTION guard_jobs_transition()
        RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE
            old_stage smallint;
            new_stage smallint;
        BEGIN
            IF OLD.id IS DISTINCT FROM NEW.id
                OR OLD.owner_id IS DISTINCT FROM NEW.owner_id
                OR OLD.job_type IS DISTINCT FROM NEW.job_type
                OR OLD.created_at IS DISTINCT FROM NEW.created_at
                OR OLD.detail_eligible_at IS DISTINCT FROM NEW.detail_eligible_at
                OR OLD.detail_must_purge_by IS DISTINCT FROM NEW.detail_must_purge_by
                OR NEW.updated_at <= OLD.updated_at
            THEN
                RAISE EXCEPTION 'immutable job identity or clock changed'
                    USING ERRCODE = '23514', CONSTRAINT = 'ck_jobs_transition';
            END IF;

            IF OLD.status IN ('SUCCEEDED', 'FAILED') THEN
                RAISE EXCEPTION 'terminal jobs cannot transition'
                    USING ERRCODE = '23514', CONSTRAINT = 'ck_jobs_transition';
            END IF;

            IF NOT (
                (OLD.status = 'QUEUED' AND NEW.status IN ('RUNNING', 'FAILED'))
                OR (OLD.status = 'RUNNING' AND NEW.status IN
                    ('RUNNING', 'RETRY_WAIT', 'SUCCEEDED', 'FAILED'))
                OR (OLD.status = 'RETRY_WAIT' AND NEW.status IN ('RUNNING', 'FAILED'))
            ) THEN
                RAISE EXCEPTION 'forbidden job status transition'
                    USING ERRCODE = '23514', CONSTRAINT = 'ck_jobs_transition';
            END IF;

            IF (OLD.status = 'QUEUED' AND NEW.status = 'RUNNING' AND NEW.attempt <> 1)
                OR (OLD.status = 'QUEUED' AND NEW.status = 'FAILED' AND NEW.attempt <> 0)
                OR (OLD.status = 'RETRY_WAIT' AND NEW.status = 'RUNNING'
                    AND NEW.attempt <> OLD.attempt + 1)
                OR (NOT (OLD.status IN ('QUEUED', 'RETRY_WAIT') AND NEW.status = 'RUNNING')
                    AND NOT (OLD.status = 'QUEUED' AND NEW.status = 'FAILED')
                    AND NEW.attempt <> OLD.attempt)
            THEN
                RAISE EXCEPTION 'job attempt changed outside a start or retry'
                    USING ERRCODE = '23514', CONSTRAINT = 'ck_jobs_transition';
            END IF;

            IF NEW.status IN ('RETRY_WAIT', 'FAILED')
                AND (NEW.stage IS DISTINCT FROM OLD.stage
                    OR NEW.progress IS DISTINCT FROM OLD.progress)
            THEN
                RAISE EXCEPTION 'waiting and failed jobs preserve the last snapshot'
                    USING ERRCODE = '23514', CONSTRAINT = 'ck_jobs_transition';
            END IF;

            old_stage := CASE OLD.stage
                WHEN 'VALIDATING_URL' THEN 0 WHEN 'CHECKING_POLICY' THEN 1
                WHEN 'EXTRACTING_METADATA' THEN 2 WHEN 'NORMALIZING_FORMATS' THEN 3
                WHEN 'READY' THEN 4 END;
            new_stage := CASE NEW.stage
                WHEN 'VALIDATING_URL' THEN 0 WHEN 'CHECKING_POLICY' THEN 1
                WHEN 'EXTRACTING_METADATA' THEN 2 WHEN 'NORMALIZING_FORMATS' THEN 3
                WHEN 'READY' THEN 4 END;
            IF new_stage < old_stage
                OR (OLD.progress IS NOT NULL AND NEW.progress IS NULL)
                OR NEW.progress < OLD.progress
            THEN
                RAISE EXCEPTION 'job stage and progress must be monotonic'
                    USING ERRCODE = '23514', CONSTRAINT = 'ck_jobs_transition';
            END IF;
            RETURN NEW;
        END;
        $$;

        CREATE TRIGGER tr_jobs_transition
        BEFORE UPDATE ON jobs
        FOR EACH ROW EXECUTE FUNCTION guard_jobs_transition();
        """
    )


def drop_job_guards() -> None:
    op.execute("DROP TRIGGER tr_jobs_transition ON jobs")
    op.execute("DROP TRIGGER tr_jobs_initial_state ON jobs")
    op.execute("DROP FUNCTION guard_jobs_transition()")
    op.execute("DROP FUNCTION guard_jobs_initial_state()")
