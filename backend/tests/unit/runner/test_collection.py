from __future__ import annotations

import json
from pathlib import Path
from zipfile import ZipFile

import pytest
from app.runner.collection import download_video_collection_zip
from app.runner.workspace import WorkspaceManager


class FakeCollectionCommands:
    async def download_collection(
        self,
        _source: object,
        output_dir: Path,
        _cwd: Path,
        *,
        max_bytes: int,
        max_entries: int,
        cookie_jar: Path | None,
    ) -> None:
        assert max_bytes > 0
        assert max_entries == 11
        assert cookie_jar is None
        (output_dir / "video-0001.mp4").write_bytes(b"first")
        (output_dir / "video-0002.webm").write_bytes(b"second")

    async def probe(self, _path: Path, _cwd: Path) -> dict[str, object]:
        return {
            "format": {"format_name": "mp4", "duration": "4"},
            "streams": [{"codec_type": "video"}],
        }


@pytest.mark.asyncio
async def test_download_video_collection_zip_contains_every_validated_video(
    tmp_path: Path,
) -> None:
    workspace = WorkspaceManager(tmp_path / "runner").create("collection")
    output = workspace.path / "artifact.zip"
    try:
        count = await download_video_collection_zip(
            "https://www.instagram.com/p/example/",
            output,
            workspace,
            expected_count=2,
            title="多个视频",
            referer="https://www.instagram.com/p/example/",
            commands=FakeCollectionCommands(),
            max_video_bytes=1024,
            max_duration_seconds=7200,
            max_assets=10,
            cookie_jar=None,
        )

        assert count == 2
        with ZipFile(output) as archive:
            assert archive.namelist() == [
                "manifest.json",
                "videos/0001.mp4",
                "videos/0002.webm",
            ]
            assert json.loads(archive.read("manifest.json")) == {
                "title": "多个视频",
                "media_kind": "video_collection",
                "asset_count": 2,
            }
            assert archive.read("videos/0002.webm") == b"second"
        assert not (workspace.path / "collection-output").exists()
    finally:
        workspace.cleanup()
