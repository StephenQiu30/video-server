from __future__ import annotations

import asyncio
import tempfile
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from app.application.downloads import EncryptedUrl, plan_from_documents
from app.domain.downloads import DownloadErrorCode, DownloadStage
from app.domain.providers import ProviderAccessContextRef

from .artifact import runner_delivery_object_key, verify_artifact
from .delivery import ArtifactDelivery
from .errors import (
    ArtifactValidationError,
    ExecutionOwnershipLost,
    ExecutionPersistenceUnavailable,
    ExecutionSourceUnavailable,
    LeaseInfrastructureError,
    LeaseLost,
    classify_runner_failure,
)
from .models import (
    ArtifactDeliveryTarget,
    DownloadExecutionSettings,
    ExecutionDisposition,
)
from .monitor import LeaseMonitor
from .ports import (
    Clock,
    ExecutionRepository,
    ExecutionRunner,
    ExecutionStorage,
    RunnerArtifactView,
    UrlDecryptor,
    WorkspaceCleaner,
)
from .transitions import ExecutionTransitions


class DownloadExecution:
    def __init__(
        self,
        *,
        repository: ExecutionRepository,
        runner: ExecutionRunner,
        storage: ExecutionStorage,
        url_cipher: UrlDecryptor,
        workspace_cleaner: WorkspaceCleaner,
        clock: Clock,
        settings: DownloadExecutionSettings,
    ) -> None:
        self._repository = repository
        self._runner = runner
        self._storage = storage
        self._url_cipher = url_cipher
        self._cleaner = workspace_cleaner
        self._clock = clock
        self._settings = settings
        self._transitions = ExecutionTransitions(repository, storage, settings, clock)
        self._delivery = ArtifactDelivery(storage, settings, clock, self._transitions)

    async def execute(self, job_id: UUID) -> ExecutionDisposition:
        try:
            claimed = await self._repository.claim_job(
                job_id,
                self._settings.worker_id,
                self._clock(),
                self._settings.lease_for,
            )
        except ExecutionSourceUnavailable:
            return ExecutionDisposition.ACK
        except Exception:
            return ExecutionDisposition.REQUEUE
        if claimed is None:
            return await self._transitions.duplicate(job_id)
        return await self._execute_claimed(job_id, claimed.attempt)

    async def _execute_claimed(
        self, job_id: UUID, attempt: int
    ) -> ExecutionDisposition:
        task_id = f"download_{job_id.hex}_{attempt}"
        workspace: Path | None = None
        delivery_key: str | None = None
        monitor = self._monitor(job_id, attempt, task_id)
        try:
            try:
                source = await self._repository.get_job_source(
                    job_id,
                    self._settings.worker_id,
                    attempt,
                    self._clock(),
                )
            except ExecutionSourceUnavailable:
                return await self._transitions.fail(
                    job_id, attempt, DownloadErrorCode.UNSUPPORTED_SOURCE
                )
            except ExecutionOwnershipLost:
                return await self._transitions.convergence(job_id)
            except Exception:
                return ExecutionDisposition.REQUEUE
            try:
                url = self._url_cipher.decrypt(
                    EncryptedUrl(
                        source.url_ciphertext,
                        source.url_nonce,
                        source.url_key_id,
                    )
                )
                plan = plan_from_documents(source.semantic_plan, source.provider_hints)
                access_context = ProviderAccessContextRef.from_document(
                    source.access_context
                )
            except Exception:
                return await self._transitions.fail(
                    job_id, attempt, DownloadErrorCode.INTERNAL_ERROR
                )
            try:
                delivery = None
                if (
                    access_context.provider_key
                    in self._settings.presigned_delivery_providers
                ):
                    delivery_key = runner_delivery_object_key(job_id, attempt)
                    upload_url = await self._storage.presigned_upload(
                        delivery_key,
                        ttl_seconds=round(
                            self._settings.artifact_delivery_ttl.total_seconds()
                        ),
                    )
                    delivery = ArtifactDeliveryTarget(delivery_key, upload_url)
                artifact = await monitor.run_download(
                    url,
                    plan,
                    provider_media_id=source.provider_media_id,
                    extractor_key=source.extractor_key,
                    access_context=access_context,
                    delivery=delivery,
                )
                workspace = artifact.workspace
            except (LeaseLost, ExecutionOwnershipLost):
                return await self._transitions.convergence(job_id)
            except (LeaseInfrastructureError, ExecutionPersistenceUnavailable):
                return ExecutionDisposition.REQUEUE
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                return await self._transitions.fail(
                    job_id, attempt, classify_runner_failure(exc)
                )
            if artifact.object_key is not None:
                if artifact.object_key != delivery_key:
                    return await self._transitions.fail(
                        job_id, attempt, DownloadErrorCode.MEDIA_VALIDATION_FAILED
                    )
                try:
                    workspace = Path(
                        tempfile.mkdtemp(
                            prefix=f"{task_id}-delivery-",
                            dir=self._settings.workspace_root,
                        )
                    )
                    target = workspace / f"artifact.{artifact.container}"
                    await self._storage.download(artifact.object_key, target)
                    artifact = _LocalArtifact.from_delivery(
                        artifact,
                        workspace=workspace,
                        path=target,
                    )
                except Exception:
                    return await self._transitions.fail(
                        job_id, attempt, DownloadErrorCode.STORAGE_UNAVAILABLE
                    )
            try:
                verified = await monitor.run_fixed(
                    lambda: verify_artifact(
                        artifact,
                        task_id=task_id,
                        shared_root=self._settings.workspace_root,
                        max_size_bytes=self._settings.max_file_size_bytes,
                    ),
                    stage=DownloadStage.VERIFYING,
                    progress=90,
                    drain_on_abort=True,
                )
            except ArtifactValidationError:
                return await self._transitions.fail(
                    job_id, attempt, DownloadErrorCode.MEDIA_VALIDATION_FAILED
                )
            except (LeaseLost, ExecutionOwnershipLost):
                return await self._transitions.convergence(job_id)
            except (LeaseInfrastructureError, ExecutionPersistenceUnavailable):
                return ExecutionDisposition.REQUEUE
            return await self._delivery.run(
                monitor,
                job_id,
                attempt,
                verified,
                source_key=delivery_key,
            )
        finally:
            with suppress(Exception):
                await self._cleaner.cleanup(task_id, workspace)
            if delivery_key is not None:
                with suppress(Exception):
                    await self._storage.delete(delivery_key)

    def _monitor(self, job_id: UUID, attempt: int, task_id: str) -> LeaseMonitor:
        return LeaseMonitor(
            repository=self._repository,
            runner=self._runner,
            job_id=job_id,
            worker_id=self._settings.worker_id,
            attempt=attempt,
            task_id=task_id,
            clock=self._clock,
            lease_for=self._settings.lease_for,
            interval=self._settings.heartbeat_interval,
        )


@dataclass(frozen=True, slots=True)
class _LocalArtifact:
    task_id: str
    workspace: Path
    artifact: Path
    object_key: None
    size_bytes: int
    sha256: str
    duration_seconds: float
    container: str
    video_streams: int
    audio_streams: int

    @classmethod
    def from_delivery(
        cls,
        source: RunnerArtifactView,
        *,
        workspace: Path,
        path: Path,
    ) -> _LocalArtifact:
        return cls(
            task_id=source.task_id,
            workspace=workspace,
            artifact=path,
            object_key=None,
            size_bytes=source.size_bytes,
            sha256=source.sha256,
            duration_seconds=source.duration_seconds,
            container=source.container,
            video_streams=source.video_streams,
            audio_streams=source.audio_streams,
        )
