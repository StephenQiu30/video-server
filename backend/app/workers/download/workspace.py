from __future__ import annotations

import asyncio
import re
import shutil
from collections.abc import Collection
from contextlib import suppress
from datetime import UTC, datetime, timedelta
from pathlib import Path

_TASK_ID = re.compile(r"[A-Za-z0-9_-]{1,64}")
_DOWNLOAD_WORKSPACE = re.compile(r"download_[0-9a-f]{32}_[1-9][0-9]*-[A-Za-z0-9_-]+$")


class SharedWorkspaceCleaner:
    def __init__(self, root: Path) -> None:
        self._root = root.resolve()

    async def cleanup(self, task_id: str, workspace: Path | None) -> None:
        if _TASK_ID.fullmatch(task_id) is None:
            return
        await asyncio.to_thread(self._cleanup, task_id, workspace)

    async def collect_orphans(
        self,
        active_task_ids: Collection[str],
        *,
        now: datetime,
        older_than: timedelta,
    ) -> tuple[str, ...]:
        if older_than <= timedelta(0):
            raise ValueError("workspace orphan age must be positive")
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("workspace cleanup clock must be timezone-aware")
        return await asyncio.to_thread(
            self._collect_orphans,
            frozenset(active_task_ids),
            now.astimezone(UTC) - older_than,
        )

    def _cleanup(self, task_id: str, workspace: Path | None) -> None:
        try:
            if self._root.is_symlink() or not self._root.is_dir():
                return
            candidates = list(self._root.iterdir())
        except OSError:
            return
        prefix = f"{task_id}-"
        for candidate in candidates:
            if not candidate.name.startswith(prefix):
                continue
            self._remove(candidate)
        if workspace is not None and workspace.name.startswith(prefix):
            self._remove(workspace)

    def _collect_orphans(
        self, active_task_ids: frozenset[str], cutoff: datetime
    ) -> tuple[str, ...]:
        try:
            if self._root.is_symlink() or not self._root.is_dir():
                return ()
            candidates = tuple(self._root.iterdir())
        except OSError:
            return ()

        removed: list[str] = []
        for candidate in candidates:
            if (
                _DOWNLOAD_WORKSPACE.fullmatch(candidate.name) is None
                or candidate.is_symlink()
                or not candidate.is_dir()
                or any(
                    candidate.name.startswith(f"{task_id}-")
                    for task_id in active_task_ids
                )
            ):
                continue
            try:
                modified_at = datetime.fromtimestamp(candidate.stat().st_mtime, tz=UTC)
            except OSError:
                continue
            if modified_at >= cutoff:
                continue
            self._remove(candidate)
            if not candidate.exists() and not candidate.is_symlink():
                removed.append(candidate.name)
        return tuple(removed)

    def _remove(self, candidate: Path) -> None:
        with suppress(OSError):
            if candidate.parent.resolve() != self._root:
                return
            if candidate.is_symlink() or not candidate.is_dir():
                candidate.unlink(missing_ok=True)
            else:
                shutil.rmtree(candidate)
