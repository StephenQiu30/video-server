from __future__ import annotations

import stat
from pathlib import Path

import pytest
from app.workers.runner._secure_file import (
    atomic_write_json,
    ensure_private_directory,
    read_private_json,
)


def test_private_directory_and_atomic_json_are_owner_only(tmp_path: Path) -> None:
    root = tmp_path / "private"
    ensure_private_directory(root)
    target = root / "state.json"

    atomic_write_json(target, {"status": "ok"})

    assert read_private_json(target, message="unsafe state") == {"status": "ok"}
    assert stat.S_IMODE(root.stat().st_mode) == 0o700
    assert stat.S_IMODE(target.stat().st_mode) == 0o600
    assert stat.S_ISREG(target.stat().st_mode)


def test_private_json_rejects_symlink_target(tmp_path: Path) -> None:
    root = tmp_path / "private"
    ensure_private_directory(root)
    destination = tmp_path / "destination.json"
    destination.write_text("{}")
    link = root / "state.json"
    link.symlink_to(destination)

    with pytest.raises(OSError):
        read_private_json(link, message="unsafe state")


def test_private_directory_rejects_symlink_path(tmp_path: Path) -> None:
    destination = tmp_path / "destination"
    destination.mkdir()
    link = tmp_path / "private"
    link.symlink_to(destination, target_is_directory=True)

    with pytest.raises(OSError):
        ensure_private_directory(link)
