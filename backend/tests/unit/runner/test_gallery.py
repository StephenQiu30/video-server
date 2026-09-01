from __future__ import annotations

import json
from pathlib import Path
from zipfile import ZipFile

import pytest
from app.runner.gallery import download_gallery_zip
from app.runner.metadata import GalleryAsset
from app.runner.workspace import WorkspaceManager


class FakeAssetCommands:
    async def download_public_asset(
        self,
        url: str,
        output: Path,
        _cwd: Path,
        *,
        referer: str,
        max_bytes: int,
    ) -> str:
        assert url.startswith("https://cdn.test/")
        assert referer == "https://www.douyin.com/note/123"
        assert max_bytes > 0
        output.write_bytes(b"\xff\xd8\xff" + url.encode())
        return "image/jpeg"


@pytest.mark.asyncio
async def test_download_gallery_zip_packages_bounded_original_assets(
    tmp_path: Path,
) -> None:
    workspace = WorkspaceManager(tmp_path / "runner").create("gallery")
    output = workspace.path / "artifact.zip"
    try:
        count = await download_gallery_zip(
            (
                GalleryAsset("https://cdn.test/one", "jpg"),
                GalleryAsset("https://cdn.test/two", "jpg"),
            ),
            output,
            workspace,
            title="官方图文",
            referer="https://www.douyin.com/note/123",
            commands=FakeAssetCommands(),
            max_asset_bytes=1024,
            max_assets=10,
        )

        assert count == 2
        with ZipFile(output) as archive:
            assert archive.namelist() == [
                "manifest.json",
                "images/0001.jpg",
                "images/0002.jpg",
            ]
            manifest = json.loads(archive.read("manifest.json"))
            assert manifest == {
                "title": "官方图文",
                "media_kind": "image_gallery",
                "asset_count": 2,
            }
            assert archive.read("images/0001.jpg").startswith(b"\xff\xd8\xff")
        assert not list(workspace.path.glob("gallery-*.source"))
    finally:
        workspace.cleanup()
