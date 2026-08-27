"""Owner-scoped, short-lived article discovery control-plane rows."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base, utc_now


class SourceDiscoveryRow(Base):
    __tablename__ = "source_discoveries"
    __table_args__ = (
        UniqueConstraint(
            "owner_hash",
            "idempotency_key",
            name="uq_source_discoveries_owner_idempotency",
        ),
        Index("ix_source_discoveries_owner_expires", "owner_hash", "expires_at"),
        CheckConstraint(
            "status IN ('ready','empty')", name="ck_source_discoveries_status"
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    owner_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_key: Mapped[str] = mapped_column(String(64), nullable=False)
    url_ciphertext: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    url_nonce: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    url_key_id: Mapped[str] = mapped_column(String(64), nullable=False)
    source_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    adapter_version: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )


class SourceDiscoveryItemRow(Base):
    __tablename__ = "source_discovery_items"
    __table_args__ = (
        UniqueConstraint(
            "discovery_id", "item_ref", name="uq_source_discovery_items_ref"
        ),
        UniqueConstraint(
            "discovery_id",
            "identity_evidence_hash",
            name="uq_source_discovery_items_identity",
        ),
        UniqueConstraint(
            "discovery_id", "position", name="uq_source_discovery_items_position"
        ),
        Index("ix_source_discovery_items_discovery", "discovery_id"),
        CheckConstraint("position >= 0", name="ck_source_discovery_items_position"),
        CheckConstraint(
            "kind IN ('official_account_native','tencent_video',"
            "'wechat_channels','unknown')",
            name="ck_source_discovery_items_kind",
        ),
        CheckConstraint(
            "decision_hint IN ('candidate','export_required','unsupported')",
            name="ck_source_discovery_items_decision",
        ),
        CheckConstraint(
            "status IN ('ready','identity_unverified')",
            name="ck_source_discovery_items_status",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    discovery_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("source_discoveries.id", ondelete="CASCADE"),
        nullable=False,
    )
    item_ref: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    child_provider: Mapped[str | None] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(Text, nullable=False)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    identity_evidence_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    decision_hint: Mapped[str] = mapped_column(String(24), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
