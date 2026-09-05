"""Atomic owner budgets and global backlog admission in the caller transaction."""

from datetime import datetime, timedelta
from typing import Literal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.quotas import QuotaExceeded, QuotaPolicy

from .models.quota import ResourceAdmissionRow
from .owner_lock import lock_owner
from .quota_queries import ACTIVE_USAGE, STORED_BYTES

AdmissionKind = Literal["download", "media_import", "document_import", "analysis"]


async def lock_admission(session: AsyncSession, owner_hash: str) -> None:
    # All admissions take these locks before any resource row lock. The global
    # lock covers only a short DB transaction, never network or worker execution.
    await lock_owner(session, owner_hash)
    await lock_owner(session, "__global_admission__")


async def reserve(
    session: AsyncSession,
    policy: QuotaPolicy,
    *,
    owner_hash: str,
    resource_id: UUID,
    kind: AdmissionKind,
    now: datetime,
    size_bytes: int | None = None,
    analysis_attempts: int = 0,
) -> None:
    """Call after replay and source validation, while holding admission locks."""
    reserved = {
        "download": policy.download_bytes + policy.thumbnail_bytes,
        "media_import": (size_bytes or 0) + policy.thumbnail_bytes,
        "document_import": (size_bytes or 0) + policy.document_normalized_bytes,
        "analysis": policy.report_bytes,
    }[kind]
    parameters = {
        "owner": owner_hash,
        "download_bytes": policy.download_bytes,
        "document_bytes": policy.document_normalized_bytes,
        "report_bytes": policy.report_bytes,
        "thumbnail_bytes": policy.thumbnail_bytes,
    }
    active = (await session.execute(ACTIVE_USAGE, parameters)).one()
    if active.global_active >= policy.max_active_global:
        raise QuotaExceeded("service_capacity_exceeded")
    if active.owner_active >= policy.max_active_per_owner:
        raise QuotaExceeded("active_task_quota_exceeded")
    daily = (
        await session.execute(
            select(
                func.count(),
                func.coalesce(func.sum(ResourceAdmissionRow.reserved_bytes), 0),
                func.coalesce(func.sum(ResourceAdmissionRow.analysis_attempts), 0),
            ).where(
                ResourceAdmissionRow.owner_hash == owner_hash,
                ResourceAdmissionRow.created_at > now - timedelta(days=1),
            )
        )
    ).one()
    for used, requested, maximum, code in (
        (daily[0], 1, policy.daily_tasks, "daily_task_quota_exceeded"),
        (daily[1], reserved, policy.daily_bytes, "daily_byte_quota_exceeded"),
        (
            daily[2],
            analysis_attempts,
            policy.daily_analysis_attempts,
            "analysis_budget_exceeded",
        ),
    ):
        if used + requested > maximum:
            raise QuotaExceeded(code, retry_after=86400)
    stored = int(await session.scalar(STORED_BYTES, parameters) or 0)
    if stored + active.reserved + reserved > policy.storage_bytes:
        raise QuotaExceeded("storage_quota_exceeded")
    session.add(
        ResourceAdmissionRow(
            id=resource_id,
            owner_hash=owner_hash,
            kind=kind,
            reserved_bytes=reserved,
            analysis_attempts=analysis_attempts,
            created_at=now,
        )
    )
