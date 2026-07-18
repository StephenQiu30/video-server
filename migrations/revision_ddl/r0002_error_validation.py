"""Frozen safe-error JSON validation used by revision 0002."""

from __future__ import annotations

from alembic import op


def create_error_validation() -> None:
    op.execute(
        r"""
        CREATE FUNCTION r0002_safe_error_payload(policy jsonb, actions jsonb)
        RETURNS boolean
        LANGUAGE plpgsql IMMUTABLE PARALLEL SAFE
        AS $$
        DECLARE
            item jsonb;
            value text;
            action_values text[] := ARRAY[]::text[];
            operation_values text[] := ARRAY[]::text[];
            user_action_values text[] := ARRAY[]::text[];
            official_url text;
        BEGIN
            IF actions IS NOT NULL THEN
                IF jsonb_typeof(actions) <> 'array' OR jsonb_array_length(actions) = 0 THEN
                    RETURN false;
                END IF;
                FOR item IN SELECT element FROM jsonb_array_elements(actions) AS element LOOP
                    IF jsonb_typeof(item) <> 'string' THEN
                        RETURN false;
                    END IF;
                    value := item #>> '{}';
                    IF value <> ALL(ARRAY[
                        'refresh_rights_statement', 'create_new_resolution',
                        'retry_resolution', 'view_supported_sources', 'open_official'
                    ]) OR value = ANY(action_values) THEN
                        RETURN false;
                    END IF;
                    action_values := array_append(action_values, value);
                END LOOP;
            END IF;

            IF policy IS NULL THEN
                RETURN NOT ('open_official' = ANY(action_values));
            END IF;
            IF jsonb_typeof(policy) <> 'object'
                OR NOT (policy ?& ARRAY[
                    'decision', 'permitted_operations', 'name',
                    'official_url', 'user_actions'
                ])
                OR policy - ARRAY[
                    'decision', 'permitted_operations', 'name',
                    'official_url', 'user_actions'
                ] <> '{}'::jsonb
                OR jsonb_typeof(policy->'decision') <> 'string'
                OR policy->>'decision' NOT IN ('allow', 'block')
                OR jsonb_typeof(policy->'permitted_operations') <> 'array'
                OR jsonb_typeof(policy->'name') <> 'string'
                OR btrim(policy->>'name') = ''
                OR octet_length(policy->>'name') > 512
                OR jsonb_typeof(policy->'user_actions') <> 'array'
            THEN
                RETURN false;
            END IF;

            FOR item IN
                SELECT element FROM jsonb_array_elements(policy->'permitted_operations') AS element
            LOOP
                IF jsonb_typeof(item) <> 'string' THEN
                    RETURN false;
                END IF;
                value := item #>> '{}';
                IF value <> ALL(ARRAY['probe', 'download'])
                    OR value = ANY(operation_values)
                THEN
                    RETURN false;
                END IF;
                operation_values := array_append(operation_values, value);
            END LOOP;

            IF policy->'official_url' = 'null'::jsonb THEN
                official_url := NULL;
            ELSIF jsonb_typeof(policy->'official_url') = 'string' THEN
                official_url := policy->>'official_url';
                IF official_url !~ '^https://[^/@?#[:space:]]+(/[^?#[:space:]]*)?$' THEN
                    RETURN false;
                END IF;
            ELSE
                RETURN false;
            END IF;

            FOR item IN SELECT element FROM jsonb_array_elements(policy->'user_actions') AS element
            LOOP
                IF jsonb_typeof(item) <> 'string' THEN
                    RETURN false;
                END IF;
                value := item #>> '{}';
                IF value <> ALL(ARRAY['view_supported_sources', 'open_official'])
                    OR value = ANY(user_action_values)
                THEN
                    RETURN false;
                END IF;
                user_action_values := array_append(user_action_values, value);
            END LOOP;

            IF 'open_official' = ANY(user_action_values) AND official_url IS NULL THEN
                RETURN false;
            END IF;
            FOREACH value IN ARRAY action_values LOOP
                IF value IN ('view_supported_sources', 'open_official')
                    AND NOT (value = ANY(user_action_values))
                THEN
                    RETURN false;
                END IF;
            END LOOP;
            RETURN NOT ('open_official' = ANY(action_values) AND official_url IS NULL);
        EXCEPTION WHEN others THEN
            RETURN false;
        END;
        $$
        """
    )


def drop_error_validation() -> None:
    op.execute("DROP FUNCTION r0002_safe_error_payload(jsonb, jsonb)")
