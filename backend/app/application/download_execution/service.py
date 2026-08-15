from __future__ import annotations

import asyncio
from contextlib import suppress
from pathlib import Path
from uuid import UUID

from app.application.downloads import EncryptedUrl, plan_from_documents
from app.domain.downloads import DownloadErrorCode, DownloadStage
from app.domain.providers import ProviderAccessContextRef

from .artifact import verify_artifact
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
from .models import DownloadExecutionSettings, ExecutionDisposition
from .monitor import LeaseMonitor
from .ports import (
    Clock,
    ExecutionRepository,
    ExecutionRunner,
    ExecutionStorage,
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
                artifact = await monitor.run_download(
                    url,
                    plan,
                    provider_media_id=source.provider_media_id,
                    extractor_key=source.extractor_key,
                    access_context=access_context,
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
            return await self._delivery.run(monitor, job_id, attempt, verified)
        finally:
            with suppress(Exception):
                await self._cleaner.cleanup(task_id, workspace)

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
