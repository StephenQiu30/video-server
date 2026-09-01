"""Bounded image-gallery assembly for public multi-asset media."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

from app.runner.errors import RunnerFailure
from app.runner.metadata import GalleryAsset
from app.runner.workspace import TaskWorkspace


async def download_gallery_zip(
    assets: tuple[GalleryAsset, ...],
    output: Path,
    workspace: TaskWorkspace,
    *,
    title: str,
    referer: str,
    commands: object,
    max_asset_bytes: int,
    max_assets: int,
) -> int:
    """Download and package validated public images without exposing their URLs."""
    if not assets or len(assets) > max_assets:
        raise RunnerFailure("format_limit_exceeded", status=413)
    download = getattr(commands, "download_public_asset", None)
    if not callable(download):
        raise RunnerFailure("runner_dependency_unavailable", status=503)

    files: list[tuple[Path, str]] = []
    try:
        for index, asset in enumerate(assets, start=1):
            source = workspace.path / f"gallery-{index:04d}.source"
            await download(
                asset.url,
                source,
                workspace.path,
                referer=referer,
                max_bytes=max_asset_bytes,
            )
            extension = _image_extension(source)
            files.append((source, f"images/{index:04d}.{extension}"))
            workspace.validate_usage()

        with zipfile.ZipFile(
            output, mode="w", compression=zipfile.ZIP_DEFLATED, compresslevel=6
        ) as archive:
            archive.writestr(
                "manifest.json",
                json.dumps(
                    {
                        "title": title,
                        "media_kind": "image_gallery",
                        "asset_count": len(files),
                    },
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
            )
            for source, name in files:
                archive.write(source, name)
        return len(files)
    finally:
        for source, _ in files:
            source.unlink(missing_ok=True)


def _image_extension(path: Path) -> str:
    with path.open("rb") as handle:
        header = handle.read(12)
    if header.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if header[:4] == b"RIFF" and header[8:12] == b"WEBP":
        return "webp"
    raise RunnerFailure("media_validation_failed", status=422)
