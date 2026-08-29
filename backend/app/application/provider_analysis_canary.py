"""Attest a completed full-video analysis as Provider release evidence."""

from __future__ import annotations

import hmac
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from time import monotonic
from typing import Protocol
from uuid import UUID

from app.application.downloads import EncryptedUrl
from app.domain.providers import (
    ProviderAccessContextRef,
    ProviderAccessMode,
    ProviderCanaryOutcome,
    ProviderCanaryResult,
    ProviderCanaryStage,
)


@dataclass(frozen=True, slots=True)
class AnalysisCanaryTarget:
    target_id: str
    provider_key: str
    profile_version: str
    access_mode: ProviderAccessMode
    egress_affinity_id: str
    client_profile_id: str
    url: str = field(repr=False)


@dataclass(frozen=True, slots=True)
class AnalysisCanaryObject:
    object_key: str
    size_bytes: int
    sha256: str


@dataclass(frozen=True, slots=True)
class AnalysisCanaryEvidence:
    source_url: EncryptedUrl
    access_context: ProviderAccessContextRef
    published_at: datetime
    objects: tuple[AnalysisCanaryObject, ...]

    def __post_init__(self) -> None:
        if self.published_at.tzinfo is None:
            raise ValueError("analysis evidence timestamp must be timezone-aware")


class AnalysisCanaryEvidenceReader(Protocol):
    async def get(
        self, analysis_job_id: UUID, *, now: datetime
    ) -> AnalysisCanaryEvidence | None: ...


class CanaryResultWriter(Protocol):
    async def save(self, result: ProviderCanaryResult) -> None: ...


class CanaryUrlDecryptor(Protocol):
    def decrypt(self, envelope: EncryptedUrl) -> str: ...


class CanaryObjectStat(Protocol):
    size_bytes: int
    sha256: str | None


class CanaryObjectStorage(Protocol):
    async def stat(self, object_key: str) -> CanaryObjectStat | None: ...


class ProviderAnalysisCanaryService:
    def __init__(
        self,
        reader: AnalysisCanaryEvidenceReader,
        writer: CanaryResultWriter,
        decryptor: CanaryUrlDecryptor,
        storage: CanaryObjectStorage,
        *,
        now: Callable[[], datetime],
        timer: Callable[[], float] = monotonic,
    ) -> None:
        self._reader = reader
        self._writer = writer
        self._decryptor = decryptor
        self._storage = storage
        self._now = now
        self._timer = timer

    async def attest(
        self, target: AnalysisCanaryTarget, analysis_job_id: UUID
    ) -> ProviderCanaryResult:
        started = self._timer()
        checked_at = self._now()
        context: ProviderAccessContextRef | None = None
        error: str | None = None
        try:
            evidence = await self._reader.get(analysis_job_id, now=checked_at)
            if evidence is None:
                raise ValueError("analysis evidence is incomplete")
            candidate_context = evidence.access_context
            source_url = self._decryptor.decrypt(evidence.source_url)
            if not (
                target.provider_key == candidate_context.provider_key
                and target.profile_version == candidate_context.profile_version
                and target.access_mode is candidate_context.access_mode
                and target.egress_affinity_id == candidate_context.egress_affinity_id
                and target.client_profile_id == candidate_context.client_profile_id
                and hmac.compare_digest(source_url, target.url)
            ):
                raise ValueError("analysis evidence does not match target")
            context = candidate_context
            for expected in evidence.objects:
                stored = await self._storage.stat(expected.object_key)
                if stored is None or stored.size_bytes != expected.size_bytes:
                    raise ValueError("analysis evidence object is unavailable")
                if stored.sha256 is not None and not hmac.compare_digest(
                    stored.sha256, expected.sha256
                ):
                    raise ValueError("analysis evidence object differs")
        except Exception:
            error = "analysis_evidence_invalid"
        result = ProviderCanaryResult(
            target_id=target.target_id,
            provider_key=target.provider_key,
            profile_version=(
                context.profile_version if context else target.profile_version
            ),
            stage=ProviderCanaryStage.ANALYSIS,
            access_mode=target.access_mode,
            outcome=(
                ProviderCanaryOutcome.SUCCEEDED
                if error is None
                else ProviderCanaryOutcome.FAILED
            ),
            stable_error_code=error,
            checked_at=checked_at,
            duration_ms=max(0, round((self._timer() - started) * 1000)),
            engine_commit=context.engine_commit if context else "evidence-unavailable",
            egress_affinity_id=(
                context.egress_affinity_id if context else target.egress_affinity_id
            ),
            client_profile_id=(
                context.client_profile_id if context else target.client_profile_id
            ),
        )
        await self._writer.save(result)
        return result
