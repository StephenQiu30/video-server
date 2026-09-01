from __future__ import annotations

import hashlib
from pathlib import Path

from app.runner.errors import RunnerFailure
from app.runner.metadata import MediaInspection, normalize_metadata
from app.runner.settings import RunnerSettings
from app.runner.url_policy import UrlPolicyError, validate_media_url


def safe_media_url(url: str) -> str:
    try:
        return validate_media_url(url).value
    except UrlPolicyError as exc:
        raise RunnerFailure("invalid_url") from exc


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_for_settings(
    payload: dict[str, object],
    settings: RunnerSettings,
) -> MediaInspection:
    return normalize_metadata(
        payload,
        max_duration_seconds=settings.runner_max_duration_seconds,
        max_candidate_streams=settings.runner_max_candidate_streams,
        max_gallery_assets=settings.runner_max_gallery_assets,
    )


def require_source_identity(
    inspection: MediaInspection,
    *,
    provider_media_id: str,
    extractor_key: str,
) -> None:
    if (
        inspection.provider_media_id != provider_media_id
        or inspection.extractor_key != extractor_key
    ):
        raise RunnerFailure("source_changed", status=409)
