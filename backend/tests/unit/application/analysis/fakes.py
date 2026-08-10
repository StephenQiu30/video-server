from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from uuid import UUID

from app.application.analysis import (
    AnalysisArtifactSnapshot,
    AnalysisCreate,
    AnalysisJobSaveResult,
    AnalysisJobSnapshot,
    AnalysisPublish,
    AnalysisResult,
    AnalysisSkillView,
    PersistenceConflict,
    PersistenceIdempotencyConflict,
    PersistenceNotFound,
)


class FakeFingerprinter:
    def fingerprint(self, namespace: str, *values: str) -> str:
        return "|".join((namespace, *values))


class FakeSkillCatalog:
    def list(self) -> tuple[AnalysisSkillView, ...]:
        return (
            AnalysisSkillView(
                id="director-breakdown",
                display_name="导演拉片",
                description="逐镜头分析",
                default_prompt="逐镜头分析视频。",
            ),
            AnalysisSkillView(
                id="highlights",
                display_name="高光提炼",
                description="识别高光",
                default_prompt="识别高光片段。",
            ),
        )

    def resolve(self, skill_id: str) -> tuple[AnalysisSkillView, str] | None:
        return next(
            (
                (skill, f"{skill.display_name}完整指令")
                for skill in self.list()
                if skill.id == skill_id
            ),
            None,
        )


class FakeRepository:
    def __init__(self) -> None:
        self.artifacts: dict[UUID, AnalysisArtifactSnapshot] = {}
        self.jobs: dict[UUID, AnalysisJobSnapshot] = {}
        self.commands: list[AnalysisCreate] = []
        self.published: list[AnalysisPublish] = []
        self.results: dict[UUID, AnalysisResult] = {}
        self.outbox_events = 0
        self._keys: dict[tuple[str, str], UUID] = {}

    async def get_artifact_for_download(
        self, download_id: UUID
    ) -> AnalysisArtifactSnapshot | None:
        return next(
            (
                artifact
                for artifact in self.artifacts.values()
                if artifact.download_id == download_id
            ),
            None,
        )

    async def create_job_and_enqueue(
        self, command: AnalysisCreate, *, now: datetime
    ) -> AnalysisJobSaveResult:
        self.commands.append(command)
        key = (command.owner_hash, command.idempotency_key)
        existing_id = self._keys.get(key)
        if existing_id is not None:
            existing = self.jobs[existing_id]
            if existing.request_fingerprint != command.request_fingerprint:
                raise PersistenceIdempotencyConflict
            return AnalysisJobSaveResult(existing, created=False)
        snapshot = AnalysisJobSnapshot.queued(command, now=now)
        self.jobs[snapshot.id] = snapshot
        self._keys[key] = snapshot.id
        self.outbox_events += 1
        return AnalysisJobSaveResult(snapshot, created=True)

    async def get_job(self, job_id: UUID) -> AnalysisJobSnapshot | None:
        return self.jobs.get(job_id)

    async def get_result(self, job_id: UUID) -> AnalysisResult | None:
        return self.results.get(job_id)

    async def cancel_job(
        self, job_id: UUID, owner_hash: str, now: datetime
    ) -> AnalysisJobSnapshot:
        current = self.jobs.get(job_id)
        if current is None or current.owner_hash != owner_hash:
            raise PersistenceNotFound
        if current.status not in {"queued", "running", "retry_wait", "cancelled"}:
            raise PersistenceConflict
        if current.status == "cancelled":
            return current
        cancelled = replace(
            current,
            status="cancelled",
            stage=None,
            error_code="cancelled",
            finished_at=now,
            updated_at=now,
        )
        self.jobs[job_id] = cancelled
        return cancelled

    async def publish_result(self, command: AnalysisPublish) -> AnalysisJobSnapshot:
        self.published.append(command)
        current = self.jobs[command.job_id]
        updated = replace(
            current,
            status="succeeded",
            stage=None,
            progress=100,
            version=current.version + 1,
            lease_owner=None,
            lease_expires_at=None,
            heartbeat_at=None,
            finished_at=command.now,
            updated_at=command.now,
        )
        self.jobs[command.job_id] = updated
        return updated


def published_result(repository: FakeRepository) -> AnalysisResult:
    return repository.published[-1].result
