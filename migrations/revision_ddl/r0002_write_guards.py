"""Frozen revision-0002 aggregate mutation guards."""

from __future__ import annotations

from alembic import op


def create_write_guards() -> None:
    # The revision that adds policy_snapshot_id must replace this trigger atomically;
    # revision 0002 intentionally permits only complete KEK rewrap updates.
    op.execute(
        """
        CREATE FUNCTION guard_source_resolution_request_update()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF ROW(
                OLD.id, OLD.owner_id, OLD.operation, OLD.job_id,
                OLD.idempotency_key_digest, OLD.request_digest,
                OLD.url_ciphertext, OLD.url_nonce,
                OLD.rights_statement_version, OLD.rights_statement_locale,
                OLD.rights_statement_sha256, OLD.rights_confirmed_at,
                OLD.created_at, OLD.detail_eligible_at, OLD.detail_must_purge_by
            ) IS DISTINCT FROM ROW(
                NEW.id, NEW.owner_id, NEW.operation, NEW.job_id,
                NEW.idempotency_key_digest, NEW.request_digest,
                NEW.url_ciphertext, NEW.url_nonce,
                NEW.rights_statement_version, NEW.rights_statement_locale,
                NEW.rights_statement_sha256, NEW.rights_confirmed_at,
                NEW.created_at, NEW.detail_eligible_at, NEW.detail_must_purge_by
            )
                OR OLD.url_wrapped_dek IS NOT DISTINCT FROM NEW.url_wrapped_dek
                OR OLD.url_wrap_nonce IS NOT DISTINCT FROM NEW.url_wrap_nonce
                OR OLD.url_key_id IS NOT DISTINCT FROM NEW.url_key_id
            THEN
                RAISE EXCEPTION 'request updates must be a complete KEK rewrap'
                    USING ERRCODE = '23514',
                        CONSTRAINT = 'ck_source_resolution_requests_immutable';
            END IF;
            RETURN NEW;
        END;
        $$;

        CREATE TRIGGER tr_source_resolution_requests_rewrap
        BEFORE UPDATE ON source_resolution_requests
        FOR EACH ROW EXECUTE FUNCTION guard_source_resolution_request_update();
        """
    )
    op.execute(
        """
        CREATE FUNCTION guard_job_event_insert()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            PERFORM 1 FROM jobs
            WHERE id = NEW.job_id
              AND owner_id = NEW.owner_id
              AND created_at = NEW.aggregate_created_at
            FOR KEY SHARE;
            IF NOT FOUND THEN
                RETURN NEW;
            END IF;
            IF NOT EXISTS (
                SELECT 1 FROM jobs
                WHERE id = NEW.job_id
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
                  AND error_retry_after_seconds IS NOT DISTINCT FROM NEW.error_retry_after_seconds
                  AND updated_at = NEW.occurred_at
            ) THEN
                RAISE EXCEPTION 'job event must match the current durable job snapshot'
                    USING ERRCODE = '23514', CONSTRAINT = 'ck_job_events_matches_job';
            END IF;
            RETURN NEW;
        END;
        $$;

        CREATE TRIGGER tr_job_events_match_job
        BEFORE INSERT ON job_events
        FOR EACH ROW EXECUTE FUNCTION guard_job_event_insert();

        CREATE FUNCTION guard_job_events_update()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'job events are append-only'
                USING ERRCODE = '23514', CONSTRAINT = 'ck_job_events_append_only';
        END;
        $$;

        CREATE TRIGGER tr_job_events_append_only
        BEFORE UPDATE ON job_events
        FOR EACH ROW EXECUTE FUNCTION guard_job_events_update();
        """
    )
    op.execute(
        """
        CREATE FUNCTION guard_outbox_update()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF ROW(
                OLD.id, OLD.resolution_request_id, OLD.job_id,
                OLD.owner_id, OLD.aggregate_created_at, OLD.kind
            ) IS DISTINCT FROM ROW(
                NEW.id, NEW.resolution_request_id, NEW.job_id,
                NEW.owner_id, NEW.aggregate_created_at, NEW.kind
            ) THEN
                RAISE EXCEPTION 'outbox message identity is immutable'
                    USING ERRCODE = '23514', CONSTRAINT = 'ck_outbox_messages_immutable';
            END IF;
            RETURN NEW;
        END;
        $$;

        CREATE TRIGGER tr_outbox_messages_immutable
        BEFORE UPDATE ON outbox_messages
        FOR EACH ROW EXECUTE FUNCTION guard_outbox_update();

        CREATE FUNCTION guard_outbox_initial_state()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF NEW.attempts <> 0
                OR NEW.lease_version <> 0
                OR NEW.claimed_by IS NOT NULL
                OR NEW.claim_token IS NOT NULL
                OR NEW.claimed_at IS NOT NULL
                OR NEW.lease_expires_at IS NOT NULL
                OR NEW.next_attempt_at IS NOT NULL
                OR NEW.published_at IS NOT NULL
                OR NEW.dead_lettered_at IS NOT NULL
                OR NEW.terminal_error_code IS NOT NULL
            THEN
                RAISE EXCEPTION 'outbox rows must be inserted in the untouched state'
                    USING ERRCODE = '23514', CONSTRAINT = 'ck_outbox_messages_initial_state';
            END IF;
            RETURN NEW;
        END;
        $$;

        CREATE TRIGGER tr_outbox_messages_initial_state
        BEFORE INSERT ON outbox_messages
        FOR EACH ROW EXECUTE FUNCTION guard_outbox_initial_state();
        """
    )


def drop_write_guards() -> None:
    op.execute("DROP TRIGGER tr_outbox_messages_immutable ON outbox_messages")
    op.execute("DROP TRIGGER tr_outbox_messages_initial_state ON outbox_messages")
    op.execute("DROP TRIGGER tr_job_events_match_job ON job_events")
    op.execute("DROP TRIGGER tr_job_events_append_only ON job_events")
    op.execute("DROP TRIGGER tr_source_resolution_requests_rewrap ON source_resolution_requests")
    op.execute("DROP FUNCTION guard_outbox_update()")
    op.execute("DROP FUNCTION guard_outbox_initial_state()")
    op.execute("DROP FUNCTION guard_job_event_insert()")
    op.execute("DROP FUNCTION guard_job_events_update()")
    op.execute("DROP FUNCTION guard_source_resolution_request_update()")
