from __future__ import annotations

import asyncio

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
)
from app.runner.presentation import inspect_response
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
            inspection = await self._inspect_source(safe_url, workspace)
            plans = build_download_options(
                inspection.streams,
                max_options=self._settings.runner_max_options,
            )
            if not plans:
                raise RunnerFailure("format_unavailable", status=409)
            return inspect_response(inspection, plans)
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
        verified = verify_probe(
            probe_payload,
            plan=plan,
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
        payload = await self._commands.inspect(safe_url, workspace.path)
        if payload.get("direct") is True:
            probe = await self._commands.probe_remote(safe_url, workspace.path)
            payload = enrich_direct_metadata(payload, probe)
        return normalize_for_settings(payload, self._settings)
