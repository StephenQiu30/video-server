"""Bounded recovery for successful local videos created before cover support."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Protocol
from uuid import UUID

from app.application.import_execution import ImportWorkspaceManager
from app.application.import_execution.ports import ImportExecutionStorage
from app.infrastructure.database.contracts import DownloadThumbnailCandidateSnapshot

_log = logging.getLogger(__name__)


class ThumbnailCandidateRepository(Protocol):
    async def list_missing_download_thumbnails(
        self, *, limit: int
    ) -> tuple[DownloadThumbnailCandidateSnapshot, ...]: ...


class ThumbnailRecovery(Protocol):
    async def recover(
        self, resource_id: UUID, owner_hash: str, artifact: Path
    ) -> bool: ...


class DownloadThumbnailBackfill:
    def __init__(
        self,
        repository: ThumbnailCandidateRepository,
        storage: ImportExecutionStorage,
        workspace: ImportWorkspaceManager,
        recovery: ThumbnailRecovery,
        *,
        interval: float,
        batch_size: int,
    ) -> None:
        if interval <= 0 or not 1 <= batch_size <= 200:
            raise ValueError("invalid thumbnail backfill settings")
        self._repository = repository
        self._storage = storage
        self._workspace = workspace
        self._recovery = recovery
        self._interval = interval
        self._batch_size = batch_size

    async def tick(self) -> int:
        recovered = 0
        candidates = await self._repository.list_missing_download_thumbnails(
            limit=self._batch_size
        )
        for candidate in candidates:
            task_id = f"import_{candidate.job_id.hex}_1"
            workspace_path: Path | None = None
            try:
                workspace = await self._workspace.create(task_id)
                workspace_path = workspace.path
                await self._storage.download(
                    candidate.object_key, workspace.input_path
                )
                if await self._recovery.recover(
                    candidate.job_id,
                    candidate.owner_hash,
                    workspace.input_path,
                ):
                    recovered += 1
            except asyncio.CancelledError:
                raise
            except Exception:
                _log.exception(
                    "thumbnail backfill failed for download %s", candidate.job_id
                )
                continue
            finally:
                try:
                    await self._workspace.cleanup(task_id, workspace_path)
                except Exception:
                    _log.exception(
                        "thumbnail backfill workspace cleanup failed for download %s",
                        candidate.job_id,
                    )
        return recovered

    async def run(self, stop: asyncio.Event) -> None:
        while not stop.is_set():
            try:
                await self.tick()
            except Exception:
                _log.exception("thumbnail backfill sweep failed")
            try:
                await asyncio.wait_for(stop.wait(), timeout=self._interval)
            except TimeoutError:
                pass
