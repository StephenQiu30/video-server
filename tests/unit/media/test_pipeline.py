import hashlib
import uuid
from pathlib import Path
from unittest.mock import patch

import pytest
from src.media.download import job_workspace, sanitize_filename
from src.media.ffmpeg import build_merge_args
from src.media.ffprobe import MediaProbeError, probe_media
from src.media.sha256 import sha256_file


def test_filename_is_bounded_and_does_not_escape_directory() -> None:
    filename = sanitize_filename("../secret\\name\x00", extension="mp4")
    assert filename == "_secret_name.mp4"
    assert len(filename) < 200


def test_job_workspace_is_removed_after_context(tmp_path: Path) -> None:
    with job_workspace(uuid.uuid4(), root=tmp_path) as workspace:
        workspace.joinpath("artifact.mp4").write_bytes(b"data")
        assert workspace.exists()
    assert list(tmp_path.iterdir()) == []


def test_merge_command_is_an_argument_array_and_stream_copy() -> None:
    args = build_merge_args(Path("v.mp4"), Path("a.m4a"), Path("out.mp4"))
    assert "-c" in args and args[args.index("-c") + 1] == "copy"
    assert "v.mp4" in args and "a.m4a" in args


def test_sha256_streaming(tmp_path: Path) -> None:
    path = tmp_path / "sample.bin"
    path.write_bytes(b"video")
    assert sha256_file(path) == hashlib.sha256(b"video").hexdigest()


def test_ffprobe_rejects_nonzero_process() -> None:
    class Completed:
        returncode = 1
        stdout = ""

    with patch("src.media.ffprobe.subprocess.run", return_value=Completed()):
        with pytest.raises(MediaProbeError):
            probe_media(Path("out.mp4"))
