from __future__ import annotations

import asyncio
import base64
import math
from dataclasses import replace
from urllib.parse import urljoin

import httpx

from app.domain.downloads import FormatSelectionError, select_streams
from app.runner.active_tasks import ActiveTaskRegistry
from app.runner.command_support import default_supervisor
from app.runner.commands import MediaCommands, ProcessRunner
from app.runner.contracts import (
    ArtifactContract,
    CancelResponse,
    DownloadRequest,
    DownloadResponse,
    InspectResponse,
    RunnerTaskStage,
    SelectedStreamsContract,
    TaskStatusResponse,
)
from app.runner.errors import RunnerFailure
from app.runner.metadata import (
    MediaInspection,
    build_download_options,
    enrich_direct_metadata,
    enrich_format_metadata,
)
from app.runner.presentation import inspect_response
from app.runner.provider_urls import (
    provider_inspection_attempts,
    provider_inspection_retry_delay,
)
from app.runner.settings import RunnerSettings
from app.runner.utilities import (
    file_sha256,
    normalize_for_settings,
    require_source_identity,
    safe_media_url,
)
from app.runner.verification import verify_probe
from app.runner.workspace import (
    TaskWorkspace,
    WorkspaceLimits,
    WorkspaceManager,
    WorkspaceViolation,
)

_MAX_PROBE_SAMPLE_ATTEMPTS = 8


class MediaRunnerService:
    def __init__(
        self,
        settings: RunnerSettings,
        *,
        supervisor: ProcessRunner | None = None,
    ) -> None:
        self._settings = settings
        self._commands = MediaCommands(
            settings,
            supervisor or default_supervisor(settings),
        )
        self._workspaces = WorkspaceManager(
            settings.runner_workspace_root,
            WorkspaceLimits(
                max_output_files=settings.runner_max_output_files,
                max_output_bytes=settings.runner_max_output_bytes,
                max_workspace_bytes=settings.runner_max_workspace_bytes,
            ),
        )
        self._active = ActiveTaskRegistry(settings.runner_max_active_tasks)

    async def inspect(self, url: str) -> InspectResponse:
        safe_url = safe_media_url(url)
        workspace = self._workspaces.create("inspect")
        try:
            try:
                async with asyncio.timeout(
                    self._settings.runner_inspect_timeout_seconds
                ):
                    inspection = await self._inspect_source(safe_url, workspace)
                    plans = build_download_options(
                        inspection.streams,
                        max_options=self._settings.runner_max_options,
                    )
                    if not plans:
                        raise RunnerFailure("format_unavailable", status=409)
                    thumbnail_data_url = await self._thumbnail_data_url(
                        inspection.thumbnail_url,
                        referer=safe_url,
                    )
                    return inspect_response(
                        inspection,
                        plans,
                        thumbnail_data_url=thumbnail_data_url,
                    )
            except TimeoutError as exc:
                raise RunnerFailure("inspection_timeout", status=504) from exc
        finally:
            workspace.cleanup()

    async def download(self, request: DownloadRequest) -> DownloadResponse:
        task = asyncio.current_task()
        if task is None:
            raise RunnerFailure("internal_error", status=500)
        self._active.register(request.task_id, task)
        workspace = None
        succeeded = False
        try:
            safe_url = safe_media_url(request.url)
            workspace = self._workspaces.create(request.task_id)
            async with asyncio.timeout(self._settings.runner_download_timeout_seconds):
                response = await self._download_in_workspace(
                    request,
                    safe_url,
                    workspace,
                )
            self._active.complete(request.task_id, task)
            succeeded = True
            return response
        except asyncio.CancelledError as exc:
            raise RunnerFailure("cancelled", status=409) from exc
        except TimeoutError as exc:
            raise RunnerFailure("download_timeout", status=504) from exc
        except WorkspaceViolation as exc:
            raise RunnerFailure("workspace_limit_exceeded", status=413) from exc
        finally:
            self._active.discard(request.task_id, task)
            if workspace is not None and not succeeded:
                workspace.cleanup()

    async def cancel(self, task_id: str) -> CancelResponse:
        self._active.cancel(task_id)
        return CancelResponse(task_id=task_id)

    async def status(self, task_id: str) -> TaskStatusResponse:
        snapshot = self._active.status(task_id)
        if snapshot is None:
            raise RunnerFailure("task_not_found", status=404)
        return TaskStatusResponse(
            task_id=task_id,
            stage=snapshot.stage,
            progress=snapshot.progress,
        )

    async def _download_in_workspace(
        self,
        request: DownloadRequest,
        safe_url: str,
        workspace: TaskWorkspace,
    ) -> DownloadResponse:
        inspection = await self._inspect_source(safe_url, workspace)
        require_source_identity(
            inspection,
            provider_media_id=request.expected_provider_media_id,
            extractor_key=request.expected_extractor_key,
        )
        plan = request.plan.to_domain()
        try:
            selection = select_streams(plan, inspection.streams)
        except FormatSelectionError as exc:
            raise RunnerFailure(exc.code.value, status=409) from exc

        inputs = [workspace.path / "video.input"]
        total_streams = 1 if selection.audio is None else 2
        self._active.update(request.task_id, RunnerTaskStage.DOWNLOADING, 10)
        await self._commands.download_stream(
            safe_url,
            selection.video.provider_id,
            inputs[0],
            workspace.path,
        )
        completed_streams = 1
        progress = 10 + 60 * completed_streams // total_streams
        self._active.update(request.task_id, RunnerTaskStage.DOWNLOADING, progress)
        if selection.audio is not None:
            inputs.append(workspace.path / "audio.input")
            await self._commands.download_stream(
                safe_url,
                selection.audio.provider_id,
                inputs[1],
                workspace.path,
            )
            completed_streams += 1
            progress = 10 + 60 * completed_streams // total_streams
            self._active.update(request.task_id, RunnerTaskStage.DOWNLOADING, progress)
        workspace.validate_usage()

        artifact = workspace.path / f"artifact.{selection.output_container.value}"
        self._active.update(request.task_id, RunnerTaskStage.REMUXING, 75)
        await self._commands.remux(
            tuple(inputs), artifact, selection.output_container, workspace.path
        )
        output = workspace.validate_outputs([artifact.name])[0]
        self._active.update(request.task_id, RunnerTaskStage.VERIFYING, 85)
        probe_payload = await self._commands.probe(artifact, workspace.path)
        verification_plan = plan
        if selection.video.width is not None and selection.video.height is not None:
            verification_plan = replace(
                plan,
                width=selection.video.width,
                height=selection.video.height,
            )
        verified = verify_probe(
            probe_payload,
            plan=verification_plan,
            expected_container=selection.output_container,
            expected_duration=inspection.duration_seconds,
            max_duration=self._settings.runner_max_duration_seconds,
            tolerance_seconds=self._settings.runner_duration_tolerance_seconds,
        )
        digest = await asyncio.to_thread(file_sha256, artifact)
        return DownloadResponse(
            task_id=request.task_id,
            workspace_path=str(workspace.path),
            artifact=ArtifactContract(
                relative_path=artifact.name,
                size_bytes=output.size,
                sha256=digest,
                duration_seconds=verified.duration_seconds,
                container=selection.output_container,
                video_streams=verified.video_streams,
                audio_streams=verified.audio_streams,
            ),
            selection=SelectedStreamsContract(
                video_provider_id=selection.video.provider_id,
                audio_provider_id=(
                    selection.audio.provider_id if selection.audio is not None else None
                ),
                output_container=selection.output_container,
            ),
        )

    async def _inspect_source(
        self, safe_url: str, workspace: TaskWorkspace
    ) -> MediaInspection:
        attempts = provider_inspection_attempts(safe_url)
        retry_delay = provider_inspection_retry_delay(safe_url)
        for attempt in range(attempts):
            try:
                payload = await self._commands.inspect(safe_url, workspace.path)
                break
            except RunnerFailure as exc:
                if exc.code != "inspection_failed" or attempt == attempts - 1:
                    raise
                await asyncio.sleep(retry_delay)
        if payload.get("direct") is True:
            probe = await self._commands.probe_remote(
                safe_url,
                workspace.path,
                referer=safe_url,
            )
            payload = enrich_direct_metadata(payload, probe)
        # Some extractors (for example Tencent Video) return only signed media
        # URLs during the initial pass. Probe those URLs before validating the
        # top-level metadata so duration and codec fields can be recovered.
        duration = payload.get("duration")
        if not isinstance(duration, (int, float)) or duration <= 0:
            payload = await self._enrich_sparse_formats(
                payload,
                workspace,
                referer=safe_url,
            )
        try:
            inspection = normalize_for_settings(payload, self._settings)
        except RunnerFailure as exc:
            if exc.code != "format_unavailable":
                raise
            inspection = None
        if inspection is not None and build_download_options(
            inspection.streams,
            max_options=1,
        ):
            return inspection
        enriched = await self._enrich_sparse_formats(
            payload,
            workspace,
            referer=safe_url,
        )
        try:
            inspection = normalize_for_settings(enriched, self._settings)
        except RunnerFailure as exc:
            if exc.code != "format_unavailable":
                raise
            inspection = None
        if inspection is not None and build_download_options(
            inspection.streams,
            max_options=1,
        ):
            return inspection
        sampled = await self._enrich_from_probe_sample(enriched, safe_url, workspace)
        return normalize_for_settings(sampled, self._settings)

    async def _enrich_sparse_formats(
        self,
        payload: dict[str, object],
        workspace: TaskWorkspace,
        *,
        referer: str,
    ) -> dict[str, object]:
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
        source_url: str,
        workspace: TaskWorkspace,
    ) -> dict[str, object]:
        formats = payload.get("formats")
        if not isinstance(formats, list):
            return payload
        candidates: list[tuple[int, dict[str, object], int]] = []
        for index, value in enumerate(formats):
            if not isinstance(value, dict):
                continue
            provider_id = value.get("format_id")
            size = value.get("filesize") or value.get("filesize_approx")
            if not isinstance(provider_id, str) or not isinstance(size, (int, float)):
                continue
            size_bytes = int(size)
            if 0 < size_bytes <= self._settings.runner_max_probe_sample_bytes:
                candidates.append((index, value, size_bytes))
        candidates.sort(key=lambda item: item[2])

        output = workspace.path / "format-probe.input"
        for index, raw, _ in candidates[:_MAX_PROBE_SAMPLE_ATTEMPTS]:
            try:
                await self._commands.download_probe_sample(
                    source_url,
                    str(raw["format_id"]),
                    output,
                    workspace.path,
                )
                probe = await self._commands.probe(output, workspace.path)
                enriched_formats = list(formats)
                enriched_formats[index] = enrich_format_metadata(raw, probe)
                enriched_payload = dict(payload)
                enriched_payload["formats"] = enriched_formats
                return enriched_payload
            except (RunnerFailure, OSError):
                continue
            finally:
                output.unlink(missing_ok=True)
        return payload

    async def _thumbnail_data_url(
        self,
        thumbnail_url: str | None,
        *,
        referer: str,
    ) -> str | None:
        if thumbnail_url is None:
            return None
        headers = {
            "Accept": "image/avif,image/webp,image/png,image/jpeg;q=0.9,*/*;q=0.5",
            "Referer": referer,
            "User-Agent": "Mozilla/5.0 (compatible; VideoDownloader/1.0)",
        }
        timeout = min(self._settings.runner_inspect_timeout_seconds, 15)
        try:
            async with httpx.AsyncClient(
                proxy=self._settings.runner_egress_proxy,
                follow_redirects=False,
                timeout=timeout,
                trust_env=False,
            ) as client:
                current_url = thumbnail_url
                for _ in range(4):
                    safe_media_url(current_url)
                    async with client.stream(
                        "GET",
                        current_url,
                        headers=headers,
                    ) as response:
                        if response.is_redirect:
                            location = response.headers.get("location")
                            if not location:
                                return None
                            current_url = urljoin(current_url, location)
                            continue
                        if response.status_code != 200:
                            return None
                        content_type = response.headers.get("content-type", "")
                        media_type = content_type.split(";", 1)[0].strip().lower()
                        if media_type not in {
                            "image/jpeg",
                            "image/png",
                            "image/webp",
                        }:
                            return None
                        content_length = response.headers.get("content-length")
                        if (
                            content_length is not None
                            and int(content_length)
                            > self._settings.runner_max_thumbnail_bytes
                        ):
                            return None
                        content = bytearray()
                        async for chunk in response.aiter_bytes():
                            content.extend(chunk)
                            if len(content) > self._settings.runner_max_thumbnail_bytes:
                                return None
                        if not content:
                            return None
                        encoded = base64.b64encode(content).decode("ascii")
                        return f"data:{media_type};base64,{encoded}"
        except (httpx.HTTPError, RunnerFailure, ValueError):
            return None
        return None


def _probe_duration(probe: dict[str, object]) -> float | None:
    format_info = probe.get("format")
    if not isinstance(format_info, dict):
        return None
    try:
        duration = float(format_info.get("duration"))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return duration if math.isfinite(duration) and duration > 0 else None
