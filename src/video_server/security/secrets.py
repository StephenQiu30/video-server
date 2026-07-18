"""Strict local secret-file loading boundary."""

from __future__ import annotations

from pathlib import Path


def load_secret_bytes(path: str | Path, *, expected_size: int | None = None) -> bytes:
    """Load an owner-only regular file without normalizing its bytes."""

    raise NotImplementedError("secret byte loading is not implemented")


def load_secret_text(path: str | Path) -> str:
    """Load a non-empty UTF-8 secret without trimming or normalization."""

    raise NotImplementedError("secret text loading is not implemented")
