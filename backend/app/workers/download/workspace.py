from __future__ import annotations

import asyncio
import re
import shutil
from contextlib import suppress
from pathlib import Path

_TASK_ID = re.compile(r"[A-Za-z0-9_-]{1,64}")


class SharedWorkspaceCleaner:
    def __init__(self, root: Path) -> None:
        self._root = root.resolve()

    async def cleanup(self, task_id: str, workspace: Path | None) -> None:
        if _TASK_ID.fullmatch(task_id) is None:
            return
        await asyncio.to_thread(self._cleanup, task_id, workspace)

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

    def _remove(self, candidate: Path) -> None:
        with suppress(OSError):
            if candidate.parent.resolve() != self._root:
                return
            if candidate.is_symlink() or not candidate.is_dir():
                candidate.unlink(missing_ok=True)
            else:
                shutil.rmtree(candidate)
