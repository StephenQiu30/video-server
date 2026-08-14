from __future__ import annotations

import hashlib
import stat
from pathlib import Path

from app.application.import_execution import (
    ImportVerificationClaim,
    ImportVerificationRejected,
)
from app.domain.imports import ImportErrorCode


def verified_source(
    path: Path,
    workspace_root: Path,
    claim: ImportVerificationClaim,
    *,
    max_size_bytes: int,
    unsafe_code: ImportErrorCode,
) -> tuple[Path, bytes, str]:
    try:
        root_stat = workspace_root.lstat()
        parent_stat = path.parent.lstat()
        file_stat = path.lstat()
        root = workspace_root.resolve(strict=True)
        parent = path.parent.resolve(strict=True)
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise ImportVerificationRejected(
            unsafe_code, "document workspace is unavailable"
        ) from exc
    if (
        not stat.S_ISDIR(root_stat.st_mode)
        or stat.S_ISLNK(root_stat.st_mode)
        or not stat.S_ISDIR(parent_stat.st_mode)
        or stat.S_ISLNK(parent_stat.st_mode)
        or not stat.S_ISREG(file_stat.st_mode)
        or stat.S_ISLNK(file_stat.st_mode)
        or not parent.is_relative_to(root)
        or parent.parent != root
        or resolved.parent != parent
    ):
        raise ImportVerificationRejected(unsafe_code, "unsafe document path")
    if (
        file_stat.st_size != claim.declared_size_bytes
        or not 0 < file_stat.st_size <= max_size_bytes
    ):
        raise ImportVerificationRejected(
            ImportErrorCode.SIZE_MISMATCH, "document size does not match"
        )
    content = resolved.read_bytes()
    digest = hashlib.sha256(content).hexdigest()
    if digest != claim.declared_sha256:
        raise ImportVerificationRejected(
            ImportErrorCode.SHA256_MISMATCH, "document SHA-256 does not match"
        )
    return resolved, content, digest
