from __future__ import annotations

import os
import shutil
import stat
import tempfile
from pathlib import Path

from .errors import MediaPreprocessingError


def workspace_root(workspace: Path) -> Path:
    try:
        if workspace.is_symlink() or not workspace.is_dir():
            raise OSError
        return workspace.resolve(strict=True)
    except OSError as exc:
        raise MediaPreprocessingError("invalid_analysis_workspace") from exc


def media_artifact(source: Path, root: Path) -> Path:
    try:
        if source.is_symlink():
            raise OSError
        info = source.stat()
        resolved = source.resolve(strict=True)
        invalid = (
            not stat.S_ISREG(info.st_mode)
            or info.st_size <= 0
            or not resolved.is_relative_to(root)
        )
        if invalid:
            raise OSError
        return resolved
    except OSError as exc:
        raise MediaPreprocessingError("invalid_media_artifact") from exc


def create_processing_directory(root: Path) -> Path:
    try:
        raw = tempfile.mkdtemp(prefix=".analysis-audio-", dir=root)
        directory = Path(raw)
        directory.chmod(0o700)
        resolved = directory.resolve(strict=True)
        if directory.is_symlink() or not resolved.is_relative_to(root):
            raise OSError
        return resolved
    except OSError as exc:
        raise MediaPreprocessingError("invalid_analysis_workspace") from exc


def read_chunk(path: Path, *, root: Path, processing: Path, max_bytes: int) -> bytes:
    try:
        if path.is_symlink():
            raise OSError
        resolved = path.resolve(strict=True)
        if not resolved.is_relative_to(root) or not resolved.is_relative_to(processing):
            raise OSError
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(resolved, flags)
    except OSError as exc:
        raise MediaPreprocessingError("invalid_chunk_output") from exc
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_size <= 0:
            raise MediaPreprocessingError("invalid_chunk_output")
        if info.st_size > max_bytes:
            raise MediaPreprocessingError("chunk_size_exceeded")
        content = _read_limited(descriptor, max_bytes)
    finally:
        os.close(descriptor)
    if not content:
        raise MediaPreprocessingError("invalid_chunk_output")
    return content


def cleanup_processing_directory(path: Path) -> None:
    try:
        info = path.lstat()
    except FileNotFoundError:
        return
    if stat.S_ISDIR(info.st_mode) and not stat.S_ISLNK(info.st_mode):
        shutil.rmtree(path, ignore_errors=True)
        return
    try:
        path.unlink()
    except FileNotFoundError:
        return


def _read_limited(descriptor: int, max_bytes: int) -> bytes:
    content = bytearray()
    while block := os.read(descriptor, min(64 * 1024, max_bytes + 1 - len(content))):
        content.extend(block)
        if len(content) > max_bytes:
            raise MediaPreprocessingError("chunk_size_exceeded")
    return bytes(content)
