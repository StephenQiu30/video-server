"""Create the append-only rights-statement catalog.

Revision ID: 0001_rights_catalog
Revises:
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001_rights_catalog"
down_revision = None
branch_labels = None
depends_on = None

_TABLE = "rights_statement_catalog"
_APPEND_ONLY_CONSTRAINT = "ck_rights_statement_catalog_append_only"


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.create_table(
        _TABLE,
        sa.Column("version", sa.Text(), nullable=False),
        sa.Column("locale", sa.Text(), nullable=False),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("statement_sha256", sa.CHAR(length=64), nullable=False),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("superseded_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            r"version ~ '^rights-[0-9]{4}-[0-9]{2}-[0-9]{2}\.[1-9][0-9]*$'",
            name=op.f("ck_rights_statement_catalog_version_format"),
        ),
        sa.CheckConstraint(
            "locale IN ('zh-CN', 'en-US')",
            name=op.f("ck_rights_statement_catalog_locale_supported"),
        ),
        sa.CheckConstraint(
            "char_length(statement) > 0",
            name=op.f("ck_rights_statement_catalog_statement_nonempty"),
        ),
        sa.CheckConstraint(
            "statement_sha256 ~ '^[0-9a-f]{64}$'",
            name=op.f("ck_rights_statement_catalog_hash_format"),
        ),
        sa.CheckConstraint(
            "statement_sha256 = encode(digest(convert_to(statement, 'UTF8'), 'sha256'), 'hex')",
            name=op.f("ck_rights_statement_catalog_hash_matches_statement"),
        ),
        sa.CheckConstraint(
            "isfinite(effective_at)",
            name=op.f("ck_rights_statement_catalog_effective_finite"),
        ),
        sa.CheckConstraint(
            "expires_at IS NULL OR isfinite(expires_at)",
            name=op.f("ck_rights_statement_catalog_expiry_finite"),
        ),
        sa.CheckConstraint(
            "superseded_at IS NULL OR isfinite(superseded_at)",
            name=op.f("ck_rights_statement_catalog_supersede_finite"),
        ),
        sa.CheckConstraint(
            "expires_at IS NULL OR expires_at > effective_at",
            name=op.f("ck_rights_statement_catalog_expiry_order"),
        ),
        sa.CheckConstraint(
            "superseded_at IS NULL OR superseded_at > effective_at",
            name=op.f("ck_rights_statement_catalog_supersede_order"),
        ),
        sa.PrimaryKeyConstraint(
            "version",
            "locale",
            name=op.f("pk_rights_statement_catalog"),
        ),
        sa.UniqueConstraint(
            "version",
            "locale",
            "statement_sha256",
            name=op.f("uq_rights_statement_catalog_attestation"),
        ),
    )
    _create_current_window_exclusion()
    _create_append_only_guard()


def downgrade() -> None:
    op.execute(f"DROP TRIGGER tr_rights_statement_catalog_no_truncate ON {_TABLE}")
    op.execute(f"DROP TRIGGER tr_rights_statement_catalog_append_only ON {_TABLE}")
    op.execute("DROP FUNCTION guard_rights_statement_catalog()")
    op.drop_table(_TABLE)


def _create_current_window_exclusion() -> None:
    op.execute(
        f"""
        ALTER TABLE {_TABLE}
        ADD CONSTRAINT ex_rights_statement_catalog_current_window
        EXCLUDE USING gist (
            locale WITH =,
            tstzrange(
                effective_at,
                GREATEST(
                    effective_at,
                    LEAST(
                        COALESCE(expires_at, 'infinity'::timestamptz),
                        COALESCE(superseded_at, 'infinity'::timestamptz)
                    )
                ),
                '[)'
            ) WITH &&
        )
        """
    )


def _create_append_only_guard() -> None:
    op.execute(
        f"""
        CREATE FUNCTION guard_rights_statement_catalog()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF TG_OP IN ('DELETE', 'TRUNCATE') THEN
                RAISE EXCEPTION 'rights statement catalog is append-only'
                    USING ERRCODE = '23514', CONSTRAINT = '{_APPEND_ONLY_CONSTRAINT}';
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
                    USING ERRCODE = '23514', CONSTRAINT = '{_APPEND_ONLY_CONSTRAINT}';
            END IF;
            RETURN NEW;
        END;
        $$;

        CREATE TRIGGER tr_rights_statement_catalog_append_only
        BEFORE UPDATE OR DELETE ON {_TABLE}
        FOR EACH ROW EXECUTE FUNCTION guard_rights_statement_catalog();

        CREATE TRIGGER tr_rights_statement_catalog_no_truncate
        BEFORE TRUNCATE ON {_TABLE}
        FOR EACH STATEMENT EXECUTE FUNCTION guard_rights_statement_catalog()
        """
    )
