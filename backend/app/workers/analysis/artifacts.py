from __future__ import annotations

import asyncio
import hashlib
import re
import shutil
import stat
import tempfile
from contextlib import suppress
from pathlib import Path
from typing import Protocol
from uuid import UUID

from app.application.analysis_execution import (
    AnalysisArtifactError,
    AnalysisArtifactSource,
    LocalAnalysisArtifact,
)

_CONTAINER = re.compile(r"[a-z0-9]{1,16}")
_SHA256 = re.compile(r"[0-9a-f]{64}")


class ArtifactStorage(Protocol):
    async def download(self, object_key: str, target: Path) -> None: ...


class LocalAnalysisArtifactLoader:
    def __init__(
        self,
        storage: ArtifactStorage,
        *,
        workspace_root: Path,
        bucket: str,
        max_source_bytes: int,
    ) -> None:
        self._storage = storage
        self._root = workspace_root.expanduser().absolute()
        self._bucket = bucket
        self._max_source_bytes = max_source_bytes

    async def prepare_root(self) -> None:
        await asyncio.to_thread(self._prepare_root)

    async def materialize(
        self,
        source: AnalysisArtifactSource,
        *,
        job_id: UUID,
        attempt: int,
    ) -> LocalAnalysisArtifact:
        _validate_source(source, self._bucket, self._max_source_bytes)
        workspace = await asyncio.to_thread(self._create_workspace, job_id, attempt)
        input_directory = workspace / "input"
        input_directory.mkdir(mode=0o700)
        local = LocalAnalysisArtifact(
            workspace,
            input_directory / "video.bin",
        )
        try:
            await self._storage.download(source.object_key, local.artifact)
            await asyncio.to_thread(
                _verify_artifact,
                local,
                source,
                self._max_source_bytes,
            )
            local.artifact.chmod(0o400)
            return local
        except asyncio.CancelledError:
            await asyncio.shield(self.cleanup(local))
            raise
        except AnalysisArtifactError:
            await self.cleanup(local)
            raise
        except Exception as exc:
            await self.cleanup(local)
            raise AnalysisArtifactError("artifact_storage_unavailable") from exc

    async def cleanup(self, local: LocalAnalysisArtifact) -> None:
        await asyncio.to_thread(self._cleanup, local.workspace)

    def _prepare_root(self) -> None:
        _reject_instruction_ancestor(self._root)
        self._root.mkdir(parents=True, exist_ok=True, mode=0o700)
        if self._root.is_symlink() or not self._root.is_dir():
            raise AnalysisArtifactError("invalid_analysis_workspace")
        self._root.chmod(0o700)

    def _create_workspace(self, job_id: UUID, attempt: int) -> Path:
        self._prepare_root()
        if attempt < 1:
            raise AnalysisArtifactError("invalid_analysis_workspace")
        path = Path(
            tempfile.mkdtemp(
                prefix=f"analysis-{job_id.hex}-{attempt}-",
                dir=self._root,
            )
        )
        path.chmod(0o700)
        resolved = path.resolve(strict=True)
        if resolved.parent != self._root.resolve(strict=True):
            raise AnalysisArtifactError("invalid_analysis_workspace")
        return resolved

    def _cleanup(self, workspace: Path) -> None:
        with suppress(OSError):
            if workspace.parent.resolve() != self._root.resolve(strict=True):
                return
            if workspace.is_symlink() or not workspace.is_dir():
                workspace.unlink(missing_ok=True)
            else:
                # Windows honors the read-only bit set on the source artifact;
                # make only this verified workspace writable before removal.
                for path in workspace.rglob("*"):
                    with suppress(OSError):
                        path.chmod(0o700)
                shutil.rmtree(workspace)


def _validate_source(
    source: AnalysisArtifactSource, bucket: str, max_source_bytes: int
) -> None:
    if (
        source.bucket != bucket
        or _SHA256.fullmatch(source.sha256) is None
        or _CONTAINER.fullmatch(source.container) is None
        or source.size_bytes <= 0
        or source.size_bytes > max_source_bytes
    ):
        raise AnalysisArtifactError("input_artifact_unavailable")


def _reject_instruction_ancestor(root: Path) -> None:
    resolved = root.expanduser().resolve(strict=False)
    if any(
        (parent / "AGENTS.md").is_file() for parent in (resolved, *resolved.parents)
    ):
        raise AnalysisArtifactError("analysis_sandbox_unavailable")


def _verify_artifact(
    local: LocalAnalysisArtifact,
    source: AnalysisArtifactSource,
    max_source_bytes: int,
) -> None:
    try:
        if local.artifact.is_symlink():
            raise OSError
        info = local.artifact.stat()
        resolved = local.artifact.resolve(strict=True)
        if (
            not stat.S_ISREG(info.st_mode)
            or not resolved.is_relative_to(local.workspace)
            or info.st_size != source.size_bytes
            or info.st_size > max_source_bytes
        ):
            raise OSError
        digest = hashlib.sha256()
        with resolved.open("rb") as stream:
            while block := stream.read(1024 * 1024):
                digest.update(block)
        if digest.hexdigest() != source.sha256:
            raise OSError
    except OSError as exc:
        raise AnalysisArtifactError("artifact_integrity_failed") from exc
