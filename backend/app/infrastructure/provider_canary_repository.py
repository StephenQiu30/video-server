from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from datetime import datetime

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.provider_canaries import ProviderEvidenceScope
from app.domain.providers import (
    ProviderAccessMode,
    ProviderCanaryOutcome,
    ProviderCanaryResult,
    ProviderCanaryStage,
)
from app.infrastructure.database.base import as_utc
from app.infrastructure.database.models import ProviderCanaryResultRow


class SqlAlchemyProviderCanaryRepository:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def save(self, result: ProviderCanaryResult) -> None:
        async with self._sessions() as session, session.begin():
            session.add(
                ProviderCanaryResultRow(
                    target_id=result.target_id,
                    provider_key=result.provider_key,
                    profile_version=result.profile_version,
                    stage=result.stage.value,
                    access_mode=result.access_mode.value,
                    outcome=result.outcome.value,
                    stable_error_code=result.stable_error_code,
                    checked_at=result.checked_at,
                    duration_ms=result.duration_ms,
                    engine_commit=result.engine_commit,
                    egress_affinity_id=result.egress_affinity_id,
                    client_profile_id=result.client_profile_id,
                    context_generation_id=result.context_generation_id,
                )
            )

    async def list_recent(
        self,
        *,
        limit_per_provider_stage: int,
        scopes: Mapping[str, ProviderEvidenceScope],
    ) -> Mapping[str, tuple[ProviderCanaryResult, ...]]:
        if limit_per_provider_stage < 1:
            raise ValueError("canary result stage limit must be positive")
        if not scopes:
            return {}
        rank = (
            func.row_number()
            .over(
                partition_by=(
                    ProviderCanaryResultRow.provider_key,
                    ProviderCanaryResultRow.stage,
                ),
                order_by=(
                    ProviderCanaryResultRow.checked_at.desc(),
                    ProviderCanaryResultRow.id.desc(),
                ),
            )
            .label("provider_stage_rank")
        )
        scope_filter = or_(
            *(
                and_(
                    ProviderCanaryResultRow.provider_key == provider_key,
                    ProviderCanaryResultRow.access_mode == scope.access_mode.value,
                    ProviderCanaryResultRow.engine_commit == scope.engine_commit,
                    ProviderCanaryResultRow.context_generation_id
                    == scope.context_generation_id,
                    *(
                        (
                            ProviderCanaryResultRow.profile_version
                            == scope.profile_version,
                        )
                        if scope.profile_version is not None
                        else ()
                    ),
                )
                for provider_key, scope in scopes.items()
            )
        )
        ranked = (
            select(ProviderCanaryResultRow.id.label("id"), rank)
            .where(scope_filter)
            .subquery()
        )
        statement = (
            select(ProviderCanaryResultRow)
            .join(ranked, ProviderCanaryResultRow.id == ranked.c.id)
            .where(ranked.c.provider_stage_rank <= limit_per_provider_stage)
            .order_by(
                ProviderCanaryResultRow.provider_key,
                ProviderCanaryResultRow.checked_at.desc(),
                ProviderCanaryResultRow.id.desc(),
            )
        )
        async with self._sessions() as session:
            rows = (await session.execute(statement)).scalars().all()
        grouped: defaultdict[str, list[ProviderCanaryResult]] = defaultdict(list)
        for row in rows:
            grouped[row.provider_key].append(_to_domain(row))
        return {key: tuple(values) for key, values in grouped.items()}

    async def latest_checked_at(
        self,
        target_id: str,
        profile_version: str,
        stage: ProviderCanaryStage,
        access_mode: ProviderAccessMode,
        engine_commit: str,
        egress_affinity_id: str,
        client_profile_id: str,
        context_generation_id: str,
    ) -> datetime | None:
        statement = select(func.max(ProviderCanaryResultRow.checked_at)).where(
            ProviderCanaryResultRow.target_id == target_id,
            ProviderCanaryResultRow.profile_version == profile_version,
            ProviderCanaryResultRow.stage == stage.value,
            ProviderCanaryResultRow.access_mode == access_mode.value,
            ProviderCanaryResultRow.engine_commit == engine_commit,
            ProviderCanaryResultRow.egress_affinity_id == egress_affinity_id,
            ProviderCanaryResultRow.client_profile_id == client_profile_id,
            ProviderCanaryResultRow.context_generation_id == context_generation_id,
        )
        async with self._sessions() as session:
            value = await session.scalar(statement)
        return None if value is None else as_utc(value)


def _to_domain(row: ProviderCanaryResultRow) -> ProviderCanaryResult:
    return ProviderCanaryResult(
        target_id=row.target_id,
        provider_key=row.provider_key,
        profile_version=row.profile_version,
        stage=ProviderCanaryStage(row.stage),
        access_mode=ProviderAccessMode(row.access_mode),
        outcome=ProviderCanaryOutcome(row.outcome),
        stable_error_code=row.stable_error_code,
        checked_at=as_utc(row.checked_at),
        duration_ms=row.duration_ms,
        engine_commit=row.engine_commit,
        egress_affinity_id=row.egress_affinity_id,
        client_profile_id=row.client_profile_id,
        context_generation_id=row.context_generation_id,
    )
