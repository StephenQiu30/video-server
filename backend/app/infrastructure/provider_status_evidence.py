"""Merge scheduled probes with verified real-download evidence."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import Mapping

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.provider_canaries import (
    ProviderCanaryReader,
    ProviderEvidenceScope,
)
from app.domain.providers import (
    ProviderAccessContextRef,
    ProviderCanaryOutcome,
    ProviderCanaryResult,
    ProviderCanaryStage,
)
from app.infrastructure.database.base import as_utc
from app.infrastructure.database.models import (
    ArtifactRow,
    DownloadJobRow,
    MediaInspectionRow,
)


class MergedProviderStatusEvidenceReader:
    def __init__(self, *readers: ProviderCanaryReader) -> None:
        self._readers = readers

    async def list_recent(
        self,
        *,
        limit_per_provider_stage: int,
        scopes: Mapping[str, ProviderEvidenceScope],
    ) -> Mapping[str, tuple[ProviderCanaryResult, ...]]:
        if limit_per_provider_stage < 1:
            raise ValueError("Provider evidence stage limit must be positive")
        sources = await asyncio.gather(
            *(
                reader.list_recent(
                    limit_per_provider_stage=limit_per_provider_stage,
                    scopes=scopes,
                )
                for reader in self._readers
            )
        )
        merged: defaultdict[
            tuple[str, ProviderCanaryStage], list[ProviderCanaryResult]
        ] = defaultdict(list)
        for source in sources:
            for provider_key, results in source.items():
                scope = scopes.get(provider_key)
                if scope is not None:
                    for item in results:
                        if _in_scope(item, scope):
                            merged[(provider_key, item.stage)].append(item)
        limited: defaultdict[str, list[ProviderCanaryResult]] = defaultdict(list)
        for (provider_key, _stage), stage_results in merged.items():
            limited[provider_key].extend(
                sorted(
                    stage_results,
                    key=lambda item: (item.checked_at, item.target_id),
                    reverse=True,
                )[:limit_per_provider_stage]
            )
        return {
            provider_key: tuple(
                sorted(
                    results,
                    key=lambda item: (item.checked_at, item.target_id),
                    reverse=True,
                )
            )
            for provider_key, results in limited.items()
        }


class SqlAlchemyDownloadEvidenceReader:
    """Project successful, retained user downloads into status evidence."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def list_recent(
        self,
        *,
        limit_per_provider_stage: int,
        scopes: Mapping[str, ProviderEvidenceScope],
    ) -> Mapping[str, tuple[ProviderCanaryResult, ...]]:
        if limit_per_provider_stage < 1:
            raise ValueError("Provider evidence stage limit must be positive")
        if not scopes:
            return {}
        async with self._sessions() as session:
            rows = (
                await session.execute(_statement(limit_per_provider_stage, scopes))
            ).all()
        grouped: defaultdict[str, list[ProviderCanaryResult]] = defaultdict(list)
        for job, artifact, inspection in rows:
            result = _download_result(job, artifact, inspection)
            if result is not None:
                grouped[result.provider_key].append(result)
        return {key: tuple(values) for key, values in grouped.items()}


def _statement(  # type: ignore[no-untyped-def]
    limit_per_provider_stage: int,
    scopes: Mapping[str, ProviderEvidenceScope],
):
    completed_at = func.coalesce(DownloadJobRow.finished_at, ArtifactRow.created_at)
    provider_key = MediaInspectionRow.metadata_json["provider_access_context"][
        "provider_key"
    ].as_string()
    profile_version = MediaInspectionRow.metadata_json["provider_access_context"][
        "profile_version"
    ].as_string()
    access_mode = MediaInspectionRow.metadata_json["provider_access_context"][
        "access_mode"
    ].as_string()
    scope_filter = or_(
        *(
            and_(
                provider_key == key,
                access_mode == scope.access_mode.value,
                *(
                    (profile_version == scope.profile_version,)
                    if scope.profile_version
                    else ()
                ),
            )
            for key, scope in scopes.items()
        )
    )
    provider_rank = func.row_number().over(
        partition_by=provider_key,
        order_by=(completed_at.desc(), DownloadJobRow.id.desc()),
    )
    ranked = (
        select(
            DownloadJobRow.id.label("job_id"),
            provider_rank.label("provider_rank"),
        )
        .join(ArtifactRow, ArtifactRow.job_id == DownloadJobRow.id)
        .join(MediaInspectionRow, MediaInspectionRow.id == DownloadJobRow.inspection_id)
        .where(
            DownloadJobRow.status == "succeeded",
            DownloadJobRow.source_kind == "remote_provider",
            ArtifactRow.deleted_at.is_(None),
            provider_key.is_not(None),
            scope_filter,
        )
        .subquery()
    )
    return (
        select(DownloadJobRow, ArtifactRow, MediaInspectionRow)
        .join(ArtifactRow, ArtifactRow.job_id == DownloadJobRow.id)
        .join(MediaInspectionRow, MediaInspectionRow.id == DownloadJobRow.inspection_id)
        .join(ranked, ranked.c.job_id == DownloadJobRow.id)
        .where(ranked.c.provider_rank <= limit_per_provider_stage)
        .order_by(provider_key, completed_at.desc(), DownloadJobRow.id.desc())
    )


def _in_scope(
    result: ProviderCanaryResult,
    scope: ProviderEvidenceScope,
) -> bool:
    return result.access_mode is scope.access_mode and (
        scope.profile_version is None or result.profile_version == scope.profile_version
    )


def _download_result(
    job: DownloadJobRow,
    artifact: ArtifactRow,
    inspection: MediaInspectionRow,
) -> ProviderCanaryResult | None:
    try:
        context = ProviderAccessContextRef.from_document(
            inspection.metadata_json.get("provider_access_context")
        )
    except (TypeError, ValueError):
        return None
    completed_at = as_utc(job.finished_at or artifact.created_at)
    started_at = as_utc(job.started_at or job.created_at)
    return ProviderCanaryResult(
        target_id=f"download:{job.id}",
        provider_key=context.provider_key,
        profile_version=context.profile_version,
        stage=ProviderCanaryStage.MEDIA,
        access_mode=context.access_mode,
        outcome=ProviderCanaryOutcome.SUCCEEDED,
        checked_at=completed_at,
        duration_ms=max(0, round((completed_at - started_at).total_seconds() * 1000)),
        engine_commit=context.engine_commit,
        egress_affinity_id=context.egress_affinity_id,
        client_profile_id=context.client_profile_id,
    )
