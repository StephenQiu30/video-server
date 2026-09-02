"""Bounded ZIP assembly for yt-dlp video collections."""

from __future__ import annotations

import json
import shutil
import zipfile
from pathlib import Path

from app.runner.errors import RunnerFailure
from app.runner.verification import verify_collection_video
from app.runner.workspace import TaskWorkspace


async def download_video_collection_zip(
    source: object,
    output: Path,
    workspace: TaskWorkspace,
    *,
    expected_count: int,
    title: str,
    referer: str,
    commands: object,
    max_video_bytes: int,
    max_duration_seconds: float,
    max_assets: int,
    cookie_jar: Path | None,
) -> int:
    """Download each playlist member, validate it, then package every member."""
    if not 1 <= expected_count <= max_assets:
        raise RunnerFailure("format_limit_exceeded", status=413)
    download = getattr(commands, "download_collection", None)
    probe = getattr(commands, "probe", None)
    if not callable(download) or not callable(probe):
        raise RunnerFailure("runner_dependency_unavailable", status=503)

    output_dir = workspace.path / "collection-output"
    output_dir.mkdir(mode=0o700)
    files: list[tuple[Path, str]] = []
    try:
        await download(
            source,
            output_dir,
            workspace.path,
            max_bytes=max_video_bytes,
            max_entries=max_assets + 1,
            cookie_jar=cookie_jar,
        )
        workspace.validate_usage()
        downloaded = _files(output_dir)
        if len(downloaded) != expected_count:
            raise RunnerFailure("source_changed", status=409)
        for index, path in enumerate(downloaded, start=1):
            verified = verify_collection_video(
                await probe(path, workspace.path),
                max_duration=max_duration_seconds,
                source_extension=path.suffix,
            )
            files.append((path, f"videos/{index:04d}.{verified.extension}"))

        with zipfile.ZipFile(
            output, mode="w", compression=zipfile.ZIP_DEFLATED, compresslevel=6
        ) as archive:
            archive.writestr(
                "manifest.json",
                json.dumps(
                    {
                        "title": title,
                        "media_kind": "video_collection",
                        "asset_count": len(files),
                    },
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
            )
            for path, name in files:
                archive.write(path, name)
        return len(files)
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def _files(directory: Path) -> list[Path]:
    candidates = sorted(directory.iterdir(), key=lambda path: path.name)
    if any(path.is_symlink() or not path.is_file() for path in candidates):
        raise RunnerFailure("media_validation_failed", status=502)
    return candidates
