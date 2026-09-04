"""Template pipeline for inspecting and enriching one provider request."""

from __future__ import annotations

import asyncio
import math
from pathlib import Path
from tempfile import TemporaryDirectory

from app.domain.providers import ProviderAccessContextRef
from app.runner.commands import MediaCommands
from app.runner.entitlements import enforce_media_rights
from app.runner.errors import RunnerFailure
from app.runner.metadata import (
    MediaInspection,
    build_download_options,
    enrich_direct_metadata,
    enrich_format_metadata,
    normalize_selected_format_metadata,
)
from app.runner.provider_registry import ProviderRequest
from app.runner.settings import RunnerSettings
from app.runner.utilities import normalize_for_settings, safe_media_url
from app.runner.workspace import TaskWorkspace

_MAX_PROBE_SAMPLE_ATTEMPTS = 8
_MAX_DURATION_PROBE_ATTEMPTS = 4


class RunnerInspectionPipeline:
    def __init__(self, settings: RunnerSettings, commands: MediaCommands) -> None:
        self._settings = settings
        self._commands = commands

    async def inspect(
        self,
        source: ProviderRequest,
        workspace: TaskWorkspace,
        *,
        context: ProviderAccessContextRef,
        cookie_jar: Path | None,
    ) -> MediaInspection:
        payload = await self._inspect_with_retry(source, workspace, cookie_jar)
        enforce_media_rights(
            payload,
            provider_key=context.provider_key,
            access_mode=context.access_mode,
        )
        payload = normalize_selected_format_metadata(payload)
        if payload.get("media_kind") in {"image_gallery", "video_collection"} or (
            str(payload.get("_type") or "").casefold() in {"playlist", "multi_video"}
            or isinstance(payload.get("entries"), list)
        ):
            return normalize_for_settings(payload, self._settings)
        if source.profile.probe_media_duration:
            payload = await self._probe_authoritative_duration(
                payload,
                source,
                workspace,
            )
        if payload.get("direct") is True and cookie_jar is None:
            probe = await self._commands.probe_remote(
                source.source_url,
                workspace.path,
                referer=source.source_url,
            )
            payload = enrich_direct_metadata(payload, probe)
        duration = payload.get("duration")
        if not isinstance(duration, (int, float)) or duration <= 0:
            payload = await self._enrich_sparse_formats(
                payload,
                workspace,
                referer=source.source_url,
                cookie_jar=cookie_jar,
                probe_authenticated_media=source.profile.probe_authenticated_media,
            )
            duration = payload.get("duration")
            if not isinstance(duration, (int, float)) or duration <= 0:
                payload = await self._enrich_from_probe_sample(
                    payload,
                    source,
                    workspace,
                    cookie_jar=cookie_jar,
                )
        inspection = self._usable_inspection(payload)
        if inspection is not None:
            return inspection
        enriched = await self._enrich_sparse_formats(
            payload,
            workspace,
            referer=source.source_url,
            cookie_jar=cookie_jar,
            probe_authenticated_media=source.profile.probe_authenticated_media,
        )
        inspection = self._usable_inspection(enriched)
        if inspection is not None:
            return inspection
        sampled = await self._enrich_from_probe_sample(
            enriched,
            source,
            workspace,
            cookie_jar=cookie_jar,
        )
        return normalize_for_settings(sampled, self._settings)

    async def _probe_authoritative_duration(
        self,
        payload: dict[str, object],
        source: ProviderRequest,
        workspace: TaskWorkspace,
    ) -> dict[str, object]:
        formats = payload.get("formats")
        if not isinstance(formats, list):
            raise RunnerFailure("inspection_failed", status=502)

        attempts = 0
        for index, value in enumerate(formats):
            if not isinstance(value, dict) or not isinstance(value.get("url"), str):
                continue
            attempts += 1
            try:
                media_url = safe_media_url(value["url"])
                probe = await self._commands.probe_remote(
                    media_url,
                    workspace.path,
                    referer=source.source_url,
                )
                duration = _probe_duration(probe)
            except (RunnerFailure, ValueError):
                duration = None
            if duration is not None:
                enriched_formats = list(formats)
                enriched_formats[index] = enrich_format_metadata(value, probe)
                enriched_payload = dict(payload)
                enriched_payload["formats"] = enriched_formats
                enriched_payload["duration"] = duration
                return enriched_payload
            if attempts == _MAX_DURATION_PROBE_ATTEMPTS:
                break
        raise RunnerFailure("inspection_failed", status=502)

    async def _inspect_with_retry(
        self,
        source: ProviderRequest,
        workspace: TaskWorkspace,
        cookie_jar: Path | None,
    ) -> dict[str, object]:
        profile = source.profile
        for attempt in range(profile.inspection_attempts):
            try:
                return await self._commands.inspect(
                    source,
                    workspace.path,
                    cookie_jar=cookie_jar,
                )
            except RunnerFailure as exc:
                retryable = exc.code in {
                    "inspection_failed",
                    "provider_temporarily_unavailable",
                }
                if not retryable or attempt == profile.inspection_attempts - 1:
                    raise
                await asyncio.sleep(profile.inspection_retry_delay)
        raise AssertionError("inspection retry loop did not terminate")

    def _usable_inspection(self, payload: dict[str, object]) -> MediaInspection | None:
        try:
            inspection = normalize_for_settings(payload, self._settings)
        except RunnerFailure as exc:
            if exc.code != "format_unavailable":
                raise
            return None
        return (
            inspection
            if build_download_options(inspection.streams, max_options=1)
            else None
        )

    async def _enrich_sparse_formats(
        self,
        payload: dict[str, object],
        workspace: TaskWorkspace,
        *,
        referer: str,
        cookie_jar: Path | None,
        probe_authenticated_media: bool,
    ) -> dict[str, object]:
        if cookie_jar is not None and not probe_authenticated_media:
            return payload
        formats = payload.get("formats")
        if not isinstance(formats, list):
            return payload
        candidates: list[tuple[int, dict[str, object], str]] = []
        for index, value in enumerate(formats):
            if not isinstance(value, dict):
                continue
            url = value.get("url")
            if isinstance(url, str):
                candidates.append((index, value, url))
            if len(candidates) == 12:
                break
        semaphore = asyncio.Semaphore(4)

        async def enrich(
            index: int,
            raw: dict[str, object],
            url: str,
        ) -> tuple[int, dict[str, object], float | None]:
            try:
                media_url = safe_media_url(url)
                async with semaphore:
                    probe = await self._commands.probe_remote(
                        media_url,
                        workspace.path,
                        referer=referer,
                    )
                return index, enrich_format_metadata(raw, probe), _probe_duration(probe)
            except (RunnerFailure, ValueError):
                return index, raw, None

        results = await asyncio.gather(
            *(enrich(index, raw, url) for index, raw, url in candidates)
        )
        enriched_formats = list(formats)
        probed_duration: float | None = None
        for index, enriched, duration in results:
            enriched_formats[index] = enriched
            if probed_duration is None and duration is not None:
                probed_duration = duration
        enriched_payload = dict(payload)
        enriched_payload["formats"] = enriched_formats
        if probed_duration is not None:
            enriched_payload["duration"] = probed_duration
        return enriched_payload

    async def _enrich_from_probe_sample(
        self,
        payload: dict[str, object],
        source: ProviderRequest,
        workspace: TaskWorkspace,
        *,
        cookie_jar: Path | None,
    ) -> dict[str, object]:
        formats = payload.get("formats")
        if not isinstance(formats, list):
            return payload
        candidates: list[tuple[int, dict[str, object], int | None]] = []
        for index, value in enumerate(formats):
            if not isinstance(value, dict):
                continue
            provider_id = value.get("format_id")
            size = value.get("filesize") or value.get("filesize_approx")
            if not isinstance(provider_id, str):
                continue
            if size is None:
                candidates.append((index, value, None))
                continue
            if isinstance(size, (int, float)):
                size_bytes = int(size)
                if 0 < size_bytes <= self._settings.runner_max_probe_sample_bytes:
                    candidates.append((index, value, size_bytes))
        candidates.sort(
            key=lambda item: (
                item[2] is None,
                item[2] if item[2] is not None else 0,
            )
        )
        for index, raw, _ in candidates[:_MAX_PROBE_SAMPLE_ATTEMPTS]:
            try:
                with TemporaryDirectory(
                    prefix="format-probe-",
                    dir=workspace.path,
                ) as directory:
                    probe_workspace = Path(directory)
                    output = probe_workspace / "sample.input"
                    await self._commands.download_probe_sample(
                        source,
                        str(raw["format_id"]),
                        output,
                        probe_workspace,
                        cookie_jar=cookie_jar,
                    )
                    probe = await self._commands.probe(output, probe_workspace)
                enriched_formats = list(formats)
                enriched_formats[index] = enrich_format_metadata(raw, probe)
                enriched_payload = dict(payload)
                enriched_payload["formats"] = enriched_formats
                probed_duration = _probe_duration(probe)
                if probed_duration is not None:
                    enriched_payload["duration"] = probed_duration
                return enriched_payload
            except (RunnerFailure, OSError):
                continue
        return payload


def _probe_duration(probe: dict[str, object]) -> float | None:
    format_info = probe.get("format")
    if not isinstance(format_info, dict):
        return None
    try:
        duration = float(format_info.get("duration"))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return duration if math.isfinite(duration) and duration > 0 else None
