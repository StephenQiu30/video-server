"""Frozen revision-0002 requirement for atomic Job/event evidence."""

from __future__ import annotations

from alembic import op


def create_event_consistency() -> None:
    op.execute(
        """
        CREATE FUNCTION guard_job_has_event()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM job_events
                WHERE job_id = NEW.id
                  AND owner_id = NEW.owner_id
                  AND aggregate_created_at = NEW.created_at
                  AND status = NEW.status
                  AND stage = NEW.stage
                  AND attempt = NEW.attempt
                  AND progress IS NOT DISTINCT FROM NEW.progress
                  AND error_code IS NOT DISTINCT FROM NEW.error_code
                  AND error_title IS NOT DISTINCT FROM NEW.error_title
                  AND error_detail IS NOT DISTINCT FROM NEW.error_detail
                  AND error_retryable IS NOT DISTINCT FROM NEW.error_retryable
                  AND error_correlation_id IS NOT DISTINCT FROM NEW.error_correlation_id
                  AND error_field IS NOT DISTINCT FROM NEW.error_field
                  AND error_policy IS NOT DISTINCT FROM NEW.error_policy
                  AND error_actions IS NOT DISTINCT FROM NEW.error_actions
                  AND error_retry_after_seconds IS NOT DISTINCT
                      FROM NEW.error_retry_after_seconds
                  AND occurred_at = NEW.updated_at
            ) THEN
                RAISE EXCEPTION 'every durable job snapshot requires a matching event'
                    USING ERRCODE = '23514', CONSTRAINT = 'ck_jobs_event_required';
            END IF;
            RETURN NULL;
        END;
        $$;

        CREATE CONSTRAINT TRIGGER tr_jobs_event_required
        AFTER INSERT OR UPDATE ON jobs
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW EXECUTE FUNCTION guard_job_has_event();
        """
    )
    op.execute(
        """
        CREATE FUNCTION guard_job_event_delete()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM jobs
                WHERE id = OLD.job_id
                  AND owner_id = OLD.owner_id
                  AND created_at = OLD.aggregate_created_at
            ) THEN
                RAISE EXCEPTION 'job events only delete with their aggregate'
                    USING ERRCODE = '23514', CONSTRAINT = 'ck_job_events_append_only';
            END IF;
            RETURN NULL;
        END;
        $$;

        CREATE CONSTRAINT TRIGGER tr_job_events_delete_with_job
        AFTER DELETE ON job_events
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW EXECUTE FUNCTION guard_job_event_delete();

        CREATE FUNCTION guard_job_events_truncate()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'job events cannot be truncated'
                USING ERRCODE = '23514', CONSTRAINT = 'ck_job_events_append_only';
        END;
        $$;

        CREATE TRIGGER tr_job_events_no_truncate
        BEFORE TRUNCATE ON job_events
        FOR EACH STATEMENT EXECUTE FUNCTION guard_job_events_truncate();
        """
    )


def drop_event_consistency() -> None:
    op.execute("DROP TRIGGER tr_job_events_no_truncate ON job_events")
    op.execute("DROP TRIGGER tr_job_events_delete_with_job ON job_events")
    op.execute("DROP TRIGGER tr_jobs_event_required ON jobs")
    op.execute("DROP FUNCTION guard_job_events_truncate()")
    op.execute("DROP FUNCTION guard_job_event_delete()")
    op.execute("DROP FUNCTION guard_job_has_event()")
