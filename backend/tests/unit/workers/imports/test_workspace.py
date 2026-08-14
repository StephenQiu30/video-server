from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from app.workers.imports.workspace import PrivateImportWorkspace

TASK_ID = "import_11111111111141118111111111111111_1"


async def test_workspace_is_private_direct_child_and_cleanup_is_scoped(
    tmp_path: Path,
) -> None:
    manager = PrivateImportWorkspace(tmp_path / "imports")

    workspace = await manager.create(TASK_ID)
    unrelated = tmp_path / "imports" / "unrelated"
    unrelated.mkdir()
    workspace.input_path.write_bytes(b"video")
    await manager.cleanup(TASK_ID, workspace.path)

    assert workspace.path.parent == (tmp_path / "imports").resolve()
    assert workspace.input_path.name == "video.mp4"
    assert not workspace.path.exists()
    assert unrelated.exists()


async def test_workspace_rejects_invalid_task_identity_and_outside_cleanup(
    tmp_path: Path,
) -> None:
    manager = PrivateImportWorkspace(tmp_path / "imports")
    outside = tmp_path / f"{TASK_ID}-outside"
    outside.mkdir()

    with pytest.raises(ValueError):
        await manager.create("../escape")
    await manager.cleanup(TASK_ID, outside)

    assert outside.exists()


async def test_orphan_cleanup_is_age_and_name_bounded(tmp_path: Path) -> None:
    current = datetime.now(UTC)
    root = tmp_path / "imports"
    manager = PrivateImportWorkspace(root)
    old = await manager.create(TASK_ID)
    fresh = await manager.create(TASK_ID)
    unrelated = root / "other-old-directory"
    unrelated.mkdir()
    old_timestamp = (current - timedelta(hours=2)).timestamp()
    os.utime(old.path, (old_timestamp, old_timestamp))
    os.utime(unrelated, (old_timestamp, old_timestamp))

    removed = await manager.cleanup_orphans(
        current, older_than=timedelta(hours=1), limit=1
    )

    assert removed == 1
    assert not old.path.exists()
    assert fresh.path.exists()
    assert unrelated.exists()
