from __future__ import annotations

import asyncio
import re
import shutil
import stat
import tempfile
from contextlib import suppress
from datetime import datetime, timedelta
from pathlib import Path

from app.application.import_execution import ImportWorkspace

_TASK_ID = re.compile(r"import_[0-9a-f]{32}_[1-9][0-9]*")


class PrivateImportWorkspace:
    def __init__(self, root: Path) -> None:
        self._root = root.resolve()

    async def create(self, task_id: str) -> ImportWorkspace:
        if _TASK_ID.fullmatch(task_id) is None:
            raise ValueError("invalid import task identity")
        return await asyncio.to_thread(self._create, task_id)

    async def cleanup(self, task_id: str, workspace: Path | None) -> None:
        if _TASK_ID.fullmatch(task_id) is None or workspace is None:
            return
        await asyncio.to_thread(self._cleanup, task_id, workspace)

    async def cleanup_orphans(
        self, now: datetime, *, older_than: timedelta, limit: int
    ) -> int:
        if older_than.total_seconds() <= 0 or not 1 <= limit <= 200:
            raise ValueError("invalid import workspace cleanup bounds")
        return await asyncio.to_thread(self._cleanup_orphans, now, older_than, limit)

    def _prepare_root(self) -> Path:
        self._root.mkdir(mode=0o700, parents=True, exist_ok=True)
        root_stat = self._root.lstat()
        root = self._root.resolve(strict=True)
        if not stat.S_ISDIR(root_stat.st_mode) or stat.S_ISLNK(root_stat.st_mode):
            raise RuntimeError("import workspace root is unsafe")
        with suppress(OSError):
            root.chmod(0o700)
        return root

    def _create(self, task_id: str) -> ImportWorkspace:
        root = self._prepare_root()
        created = Path(tempfile.mkdtemp(prefix=f"{task_id}-", dir=root))
        created.chmod(0o700)
        resolved = created.resolve(strict=True)
        if resolved.parent != root:
            self._remove(created, root)
            raise RuntimeError("import workspace escaped its root")
        return ImportWorkspace(resolved, resolved / "video.mp4")

    def _cleanup(self, task_id: str, workspace: Path) -> None:
        root = self._prepare_root()
        if not workspace.name.startswith(f"{task_id}-"):
            return
        self._remove(workspace, root)

    def _cleanup_orphans(self, now: datetime, older_than: timedelta, limit: int) -> int:
        root = self._prepare_root()
        cutoff = now.timestamp() - older_than.total_seconds()
        try:
            candidates = sorted(root.iterdir(), key=lambda item: item.name)
        except OSError:
            return 0
        removed = 0
        for candidate in candidates:
            if removed >= limit or not _workspace_name(candidate.name):
                continue
            try:
                modified_at = candidate.lstat().st_mtime
            except OSError:
                continue
            if modified_at > cutoff:
                continue
            self._remove(candidate, root)
            if not candidate.exists() and not candidate.is_symlink():
                removed += 1
        return removed

    @staticmethod
    def _remove(candidate: Path, root: Path) -> None:
        with suppress(OSError):
            if candidate.parent.resolve() != root:
                return
            candidate_stat = candidate.lstat()
            if stat.S_ISLNK(candidate_stat.st_mode) or not stat.S_ISDIR(
                candidate_stat.st_mode
            ):
                candidate.unlink(missing_ok=True)
            else:
                shutil.rmtree(candidate)


def _workspace_name(value: str) -> bool:
    prefix, separator, suffix = value.rpartition("-")
    return bool(separator and suffix and _TASK_ID.fullmatch(prefix))
