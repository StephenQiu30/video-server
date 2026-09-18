from __future__ import annotations

import json
from pathlib import Path
from zipfile import ZipFile

import pytest
from app.workers.runner.gallery import download_gallery_zip
from app.workers.runner.metadata import GalleryAsset
from app.workers.runner.workspace import WorkspaceManager


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


@pytest.mark.asyncio
async def test_gallery_failure_cleans_partial_member_and_archive(
    tmp_path: Path,
) -> None:
    from app.workers.runner.errors import RunnerFailure

    class PartialCommands:
        async def download_public_asset(self, _url, output, _cwd, **_kwargs):
            output.write_bytes(b"partial image")
            raise RunnerFailure("download_timeout", status=504)

    workspace = WorkspaceManager(tmp_path / "runner").create("partial")
    output = workspace.path / "artifact.zip"
    output.write_bytes(b"partial archive")
    try:
        with pytest.raises(RunnerFailure) as caught:
            await download_gallery_zip(
                (GalleryAsset("https://cdn.test/photo", "jpg"),),
                output,
                workspace,
                title="Photo",
                referer="https://cdn.test/",
                commands=PartialCommands(),
                max_asset_bytes=1024,
                max_assets=10,
            )
        assert caught.value.code == "download_timeout"
        assert not output.exists()
        assert not list(workspace.path.glob("gallery-*.source"))
    finally:
        workspace.cleanup()
