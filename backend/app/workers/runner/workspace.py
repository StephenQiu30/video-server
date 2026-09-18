from __future__ import annotations

import os
import re
import shutil
import stat
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

_TASK_ID = re.compile(r"[A-Za-z0-9_-]{1,64}")


class WorkspaceViolation(ValueError):
    """A task workspace or declared output exceeds the runner policy."""


@dataclass(frozen=True, slots=True)
class WorkspaceLimits:
    max_output_files: int = 3
    max_output_bytes: int = 2 * 1024**3
    max_workspace_bytes: int = 4 * 1024**3

    def __post_init__(self) -> None:
        if (
            min(
                self.max_output_files,
                self.max_output_bytes,
                self.max_workspace_bytes,
            )
            <= 0
        ):
            raise ValueError("workspace limits must be positive")


@dataclass(frozen=True, slots=True)
class OutputFile:
    relative_path: Path
    size: int


class WorkspaceManager:
    def __init__(self, root: Path, limits: WorkspaceLimits | None = None) -> None:
        self._root = root
        self._limits = limits or WorkspaceLimits()

    def create(self, task_id: str) -> TaskWorkspace:
        if not isinstance(task_id, str) or _TASK_ID.fullmatch(task_id) is None:
            raise WorkspaceViolation("task identifier is unsafe")
        self._root.mkdir(mode=0o700, parents=True, exist_ok=True)
        if self._root.is_symlink() or not self._root.is_dir():
            raise WorkspaceViolation("workspace root must be a real directory")
        root = self._root.resolve()
        path = Path(tempfile.mkdtemp(prefix=f"{task_id}-", dir=root))
        path.chmod(0o700)
        return TaskWorkspace(root=root, path=path, limits=self._limits)


@dataclass(frozen=True, slots=True)
class TaskWorkspace:
    root: Path
    path: Path
    limits: WorkspaceLimits

    def validate_usage(self) -> int:
        self._ensure_trusted()
        total = 0
        for directory, names, files in os.walk(self.path, followlinks=False):
            base = Path(directory)
            for name in names:
                if (base / name).is_symlink():
                    raise WorkspaceViolation("workspace cannot contain symlinks")
            for name in files:
                candidate = base / name
                metadata = candidate.lstat()
                if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
                    raise WorkspaceViolation("workspace can contain regular files only")
                total += metadata.st_size
                if total > self.limits.max_workspace_bytes:
                    raise WorkspaceViolation("workspace size limit exceeded")
        return total

    def validate_outputs(self, paths: Sequence[str | Path]) -> tuple[OutputFile, ...]:
        if len(paths) > self.limits.max_output_files:
            raise WorkspaceViolation("output file count limit exceeded")
        self.validate_usage()

        outputs: list[OutputFile] = []
        seen: set[Path] = set()
        output_bytes = 0
        for value in paths:
            relative = Path(value)
            escapes = relative.is_absolute() or ".." in relative.parts
            if escapes or relative == Path("."):
                raise WorkspaceViolation("output path must remain inside the workspace")
            if relative in seen:
                raise WorkspaceViolation("duplicate output path")
            seen.add(relative)
            candidate = self.path / relative
            try:
                metadata = candidate.lstat()
            except FileNotFoundError as exc:
                raise WorkspaceViolation("declared output does not exist") from exc
            if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
                raise WorkspaceViolation("output must be a regular file")
            output_bytes += metadata.st_size
            if output_bytes > self.limits.max_output_bytes:
                raise WorkspaceViolation("output file size limit exceeded")
            outputs.append(OutputFile(relative, metadata.st_size))
        return tuple(outputs)

    def cleanup(self) -> None:
        if not self.path.exists() and not self.path.is_symlink():
            return
        self._ensure_trusted()
        shutil.rmtree(self.path)

    def _ensure_trusted(self) -> None:
        if self.root.is_symlink() or not self.root.is_dir():
            raise WorkspaceViolation("workspace root is no longer trusted")
        if self.path.parent != self.root or self.path.is_symlink():
            raise WorkspaceViolation("task workspace is no longer trusted")
        if not self.path.is_dir():
            raise WorkspaceViolation("task workspace does not exist")
