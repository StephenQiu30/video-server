from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest
from app.runner.workspace import WorkspaceLimits, WorkspaceManager, WorkspaceViolation


def make_manager(tmp_path: Path, **limits: int) -> WorkspaceManager:
    return WorkspaceManager(tmp_path / "runner", WorkspaceLimits(**limits))


def test_allocates_private_unique_task_workspace(tmp_path: Path) -> None:
    manager = make_manager(tmp_path)

    first = manager.create("job_123")
    second = manager.create("job_123")

    assert first.path != second.path
    if os.name == "posix":
        assert stat.S_IMODE(first.path.stat().st_mode) == 0o700
    first.cleanup()
    second.cleanup()
    assert not first.path.exists()
    assert not second.path.exists()


def test_validates_regular_outputs_and_sizes(tmp_path: Path) -> None:
    workspace = make_manager(
        tmp_path,
        max_output_files=3,
        max_output_bytes=10,
        max_workspace_bytes=20,
    ).create("job")
    (workspace.path / "final.mp4").write_bytes(b"video")

    outputs = workspace.validate_outputs(["final.mp4"])

    assert outputs[0].relative_path == Path("final.mp4")
    assert outputs[0].size == 5


def test_rejects_too_many_output_files(tmp_path: Path) -> None:
    workspace = make_manager(tmp_path, max_output_files=2).create("job")
    for name in ("a.mp4", "b.mp4", "c.mp4"):
        (workspace.path / name).write_bytes(b"x")

    with pytest.raises(WorkspaceViolation):
        workspace.validate_outputs(["a.mp4", "b.mp4", "c.mp4"])


def test_rejects_oversized_output_and_workspace(tmp_path: Path) -> None:
    output_limited = make_manager(
        tmp_path / "output",
        max_output_bytes=3,
        max_workspace_bytes=10,
    ).create("job")
    (output_limited.path / "large.mp4").write_bytes(b"1234")

    with pytest.raises(WorkspaceViolation):
        output_limited.validate_outputs(["large.mp4"])

    workspace_limited = make_manager(
        tmp_path / "workspace",
        max_output_bytes=10,
        max_workspace_bytes=5,
    ).create("job")
    (workspace_limited.path / "part-a").write_bytes(b"123")
    (workspace_limited.path / "part-b").write_bytes(b"456")

    with pytest.raises(WorkspaceViolation):
        workspace_limited.validate_usage()


def test_output_size_limit_applies_to_all_declared_outputs(tmp_path: Path) -> None:
    workspace = make_manager(
        tmp_path,
        max_output_bytes=5,
        max_workspace_bytes=10,
    ).create("job")
    (workspace.path / "video").write_bytes(b"123")
    (workspace.path / "audio").write_bytes(b"456")

    with pytest.raises(WorkspaceViolation):
        workspace.validate_outputs(["video", "audio"])


def test_rejects_symlink_and_directory_traversal_outputs(tmp_path: Path) -> None:
    workspace = make_manager(tmp_path).create("job")
    outside = tmp_path / "outside.mp4"
    outside.write_bytes(b"x")
    (workspace.path / "link.mp4").symlink_to(outside)

    with pytest.raises(WorkspaceViolation):
        workspace.validate_outputs(["link.mp4"])
    with pytest.raises(WorkspaceViolation):
        workspace.validate_outputs(["../outside.mp4"])


def test_rejects_workspace_root_replaced_by_symlink(tmp_path: Path) -> None:
    workspace = make_manager(tmp_path).create("job")
    path = workspace.path
    path.rmdir()
    outside = tmp_path / "outside-dir"
    outside.mkdir()
    (outside / "artifact.mp4").write_bytes(b"x")
    path.symlink_to(outside, target_is_directory=True)

    with pytest.raises(WorkspaceViolation):
        workspace.validate_outputs(["artifact.mp4"])


@pytest.mark.parametrize("task_id", ["", "../escape", "space value", "a" * 65])
def test_rejects_unsafe_task_identifier(tmp_path: Path, task_id: str) -> None:
    with pytest.raises(WorkspaceViolation):
        make_manager(tmp_path).create(task_id)
