"""Create the four MVP media/download tables.

Revision ID: 0001_initial_media_download
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial_media_download"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    media_uuid = sa.Uuid()

    op.create_table(
        "media_sources",
        sa.Column("id", media_uuid, nullable=False),
        sa.Column("owner_token_hash", sa.CHAR(length=64), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("source_host", sa.String(length=253), nullable=False),
        sa.Column("extractor_key", sa.String(length=100), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=True),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("thumbnail_url", sa.Text(), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("inspect_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "duration_seconds IS NULL OR duration_seconds >= 0",
            name="ck_media_sources_duration",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("owner_token_hash", "id", name="uq_media_sources_owner_id"),
    )
    op.create_index(
        "ix_media_sources_owner_inspect_expires",
        "media_sources",
        ["owner_token_hash", "inspect_expires_at"],
    )
    op.create_index(
        "ix_media_sources_inspect_expires", "media_sources", ["inspect_expires_at"]
    )

    op.create_table(
        "media_formats",
        sa.Column("id", media_uuid, nullable=False),
        sa.Column("source_id", media_uuid, nullable=False),
        sa.Column("video_format_id", sa.String(length=100), nullable=False),
        sa.Column("audio_format_id", sa.String(length=100), nullable=True),
        sa.Column("label", sa.String(length=50), nullable=False),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("fps", sa.Numeric(6, 2), nullable=True),
        sa.Column("container", sa.String(length=20), nullable=False),
        sa.Column("video_codec", sa.String(length=100), nullable=False),
        sa.Column("audio_codec", sa.String(length=100), nullable=False),
        sa.Column("estimated_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("requires_merge", sa.Boolean(), nullable=False),
        sa.Column("sort_order", sa.SmallInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("width IS NULL OR width > 0", name="ck_media_formats_width"),
        sa.CheckConstraint(
            "height IS NULL OR height > 0", name="ck_media_formats_height"
        ),
        sa.CheckConstraint("fps IS NULL OR fps > 0", name="ck_media_formats_fps"),
        sa.CheckConstraint(
            "estimated_size_bytes IS NULL OR estimated_size_bytes >= 0",
            name="ck_media_formats_size",
        ),
        sa.CheckConstraint("sort_order >= 0", name="ck_media_formats_sort"),
        sa.ForeignKeyConstraint(
            ["source_id"], ["media_sources.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_id", "sort_order", name="uq_media_formats_source_sort"
        ),
        sa.UniqueConstraint("source_id", "id", name="uq_media_formats_source_id"),
    )
    op.create_index("ix_media_formats_source_id", "media_formats", ["source_id"])

    op.create_table(
        "download_jobs",
        sa.Column("id", media_uuid, nullable=False),
        sa.Column("owner_token_hash", sa.CHAR(length=64), nullable=False),
        sa.Column("client_request_id", media_uuid, nullable=False),
        sa.Column("source_id", media_uuid, nullable=False),
        sa.Column("format_id", media_uuid, nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("stage", sa.String(length=20), nullable=True),
        sa.Column("progress_percent", sa.SmallInteger(), nullable=True),
        sa.Column("downloaded_bytes", sa.BigInteger(), nullable=True),
        sa.Column("total_bytes", sa.BigInteger(), nullable=True),
        sa.Column("error_code", sa.String(length=80), nullable=True),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "status IN ('queued','running','succeeded','failed','expired')",
            name="ck_download_jobs_status",
        ),
        sa.CheckConstraint(
            "stage IS NULL OR stage IN ("
            "'downloading','merging','verifying','uploading')",
            name="ck_download_jobs_stage",
        ),
        sa.CheckConstraint(
            "progress_percent IS NULL OR progress_percent BETWEEN 0 AND 100",
            name="ck_download_jobs_progress",
        ),
        sa.CheckConstraint(
            "downloaded_bytes IS NULL OR downloaded_bytes >= 0",
            name="ck_download_jobs_downloaded_bytes",
        ),
        sa.CheckConstraint(
            "total_bytes IS NULL OR total_bytes >= 0",
            name="ck_download_jobs_total_bytes",
        ),
        sa.CheckConstraint("version >= 0", name="ck_download_jobs_version"),
        sa.ForeignKeyConstraint(
            ["owner_token_hash", "source_id"],
            ["media_sources.owner_token_hash", "media_sources.id"],
            name="fk_download_jobs_source_owner",
        ),
        sa.ForeignKeyConstraint(
            ["source_id", "format_id"],
            ["media_formats.source_id", "media_formats.id"],
            name="fk_download_jobs_format_source",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_id", name="uq_download_jobs_source"),
        sa.UniqueConstraint(
            "owner_token_hash",
            "client_request_id",
            name="uq_download_jobs_owner_request",
        ),
    )
    op.create_index(
        "ix_download_jobs_status_published", "download_jobs", ["status", "published_at"]
    )
    op.create_index("ix_download_jobs_format_id", "download_jobs", ["format_id"])
    op.create_index("ix_download_jobs_created_at", "download_jobs", ["created_at"])

    op.create_table(
        "artifacts",
        sa.Column("id", media_uuid, nullable=False),
        sa.Column("download_job_id", media_uuid, nullable=False),
        sa.Column("object_key", sa.String(length=500), nullable=False),
        sa.Column("file_name", sa.String(length=500), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("sha256", sa.CHAR(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("size_bytes > 0", name="ck_artifacts_size"),
        sa.ForeignKeyConstraint(
            ["download_job_id"], ["download_jobs.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("download_job_id"),
        sa.UniqueConstraint("object_key"),
    )
    op.create_index("ix_artifacts_expires_at", "artifacts", ["expires_at"])
    op.create_index("ix_artifacts_deleted_at", "artifacts", ["deleted_at"])


def downgrade() -> None:
    op.drop_index("ix_artifacts_deleted_at", table_name="artifacts")
    op.drop_index("ix_artifacts_expires_at", table_name="artifacts")
    op.drop_table("artifacts")
    op.drop_index("ix_download_jobs_created_at", table_name="download_jobs")
    op.drop_index("ix_download_jobs_format_id", table_name="download_jobs")
    op.drop_index("ix_download_jobs_status_published", table_name="download_jobs")
    op.drop_table("download_jobs")
    op.drop_index("ix_media_formats_source_id", table_name="media_formats")
    op.drop_table("media_formats")
    op.drop_index("ix_media_sources_inspect_expires", table_name="media_sources")
    op.drop_index("ix_media_sources_owner_inspect_expires", table_name="media_sources")
    op.drop_table("media_sources")
