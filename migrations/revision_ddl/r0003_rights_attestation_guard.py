"""Revision-0003 guard for immutable rights-attestation history."""

from __future__ import annotations

from alembic import op

_APPEND_ONLY_CONSTRAINT = "ck_rights_statement_catalog_append_only"
_ATTESTATION_CONSTRAINT = "ck_rights_statement_catalog_supersede_after_attestation"


def install_rights_catalog_guard(*, protect_attestations: bool) -> None:
    attestation_guard = ""
    if protect_attestations:
        attestation_guard = f"""
            IF EXISTS (
                SELECT 1
                FROM source_resolution_requests AS request
                WHERE request.rights_statement_version = OLD.version
                  AND request.rights_statement_locale = OLD.locale
                  AND request.rights_confirmed_at >= NEW.superseded_at
            ) THEN
                RAISE EXCEPTION 'rights supersession cannot rewrite attestation history'
                    USING ERRCODE = '23514',
                        CONSTRAINT = '{_ATTESTATION_CONSTRAINT}';
            END IF;
        """
    op.execute(
        f"""
        CREATE OR REPLACE FUNCTION guard_rights_statement_catalog()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF TG_OP IN ('DELETE', 'TRUNCATE') THEN
                RAISE EXCEPTION 'rights statement catalog is append-only'
                    USING ERRCODE = '23514',
                        CONSTRAINT = '{_APPEND_ONLY_CONSTRAINT}';
            END IF;
            IF OLD.version IS DISTINCT FROM NEW.version
                OR OLD.locale IS DISTINCT FROM NEW.locale
                OR OLD.statement IS DISTINCT FROM NEW.statement
                OR OLD.statement_sha256 IS DISTINCT FROM NEW.statement_sha256
                OR OLD.effective_at IS DISTINCT FROM NEW.effective_at
                OR OLD.expires_at IS DISTINCT FROM NEW.expires_at
                OR OLD.superseded_at IS NOT NULL
                OR NEW.superseded_at IS NULL
            THEN
                RAISE EXCEPTION 'rights statement catalog is append-only'
                    USING ERRCODE = '23514',
                        CONSTRAINT = '{_APPEND_ONLY_CONSTRAINT}';
            END IF;
            {attestation_guard}
            RETURN NEW;
        END;
        $$
        """
    )
