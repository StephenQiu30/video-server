"""HMAC-authenticated client for the isolated Media Runner service."""

from __future__ import annotations

import math
import re
import secrets
import time
from collections.abc import Callable
from pathlib import Path
from typing import TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from app.application.downloads import (
    MediaInspectionFailure,
    RunnerFormat,
    RunnerInspection,
)
from app.domain.downloads import DownloadPlan
from app.infrastructure.media_runner_models import (
    MediaRunnerClientError,
    RunnerArtifact,
    RunnerProgress,
    download_stage,
)
from app.runner.contracts import (
    CancelCommand,
    CancelResponse,
    DownloadPlanContract,
    DownloadRequest,
    DownloadResponse,
    InspectRequest,
    InspectResponse,
    TaskStatusResponse,
)
from app.runner.signing import sign_request

_TASK_ID = re.compile(r"[A-Za-z0-9_-]{1,64}")
ResponseModel = TypeVar("ResponseModel", bound=BaseModel)


class MediaRunnerHttpClient:
    def __init__(
        self,
        *,
        base_url: str,
        secret: bytes,
        workspace_root: Path,
        inspect_timeout_seconds: float,
        download_timeout_seconds: float,
        client: httpx.AsyncClient | None = None,
        clock: Callable[[], int] | None = None,
        nonce: Callable[[], str] | None = None,
    ) -> None:
        if len(secret) < 32:
            raise ValueError("runner HMAC secret must contain at least 32 bytes")
        self._secret = secret
        self._workspace_root = workspace_root.resolve()
        self._inspect_timeout = inspect_timeout_seconds
        self._download_timeout = download_timeout_seconds
        self._clock = clock or (lambda: int(time.time()))
        self._nonce = nonce or (lambda: secrets.token_urlsafe(24))
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(base_url=base_url)

    async def inspect(self, url: str) -> RunnerInspection:
        try:
            response = await self._request(
                "POST",
                "/internal/v1/inspect",
                InspectRequest(url=url).model_dump_json().encode(),
                InspectResponse,
                self._inspect_timeout,
            )
        except MediaRunnerClientError as exc:
            raise MediaInspectionFailure(exc.code) from exc
        return RunnerInspection(
            extractor_key=response.media.extractor_key,
            provider_media_id=response.media.provider_media_id,
            title=response.media.title,
            duration_seconds=math.ceil(response.media.duration_seconds),
            formats=tuple(
                RunnerFormat(item.label, item.plan.to_domain())
                for item in response.options
            ),
        )

    async def download(
        self,
        task_id: str,
        url: str,
        plan: DownloadPlan,
        *,
        expected_provider_media_id: str,
        expected_extractor_key: str,
    ) -> RunnerArtifact:
        self._validate_task_id(task_id)
        body = (
            DownloadRequest(
                task_id=task_id,
                url=url,
                expected_provider_media_id=expected_provider_media_id,
                expected_extractor_key=expected_extractor_key,
                plan=DownloadPlanContract.from_domain(plan),
            )
            .model_dump_json()
            .encode()
        )
        response = await self._request(
            "POST",
            "/internal/v1/download",
            body,
            DownloadResponse,
            self._download_timeout,
        )
        workspace = Path(response.workspace_path).resolve()
        artifact = (workspace / response.artifact.relative_path).resolve()
        outside_root = not workspace.is_relative_to(self._workspace_root)
        outside_workspace = not artifact.is_relative_to(workspace)
        if outside_root or outside_workspace:
            raise MediaRunnerClientError("invalid_artifact_path", 502)
        return RunnerArtifact(
            task_id=response.task_id,
            workspace=workspace,
            artifact=artifact,
            size_bytes=response.artifact.size_bytes,
            sha256=response.artifact.sha256,
            duration_seconds=response.artifact.duration_seconds,
            container=response.artifact.container.value,
            video_streams=response.artifact.video_streams,
            audio_streams=response.artifact.audio_streams,
        )

    async def status(self, task_id: str) -> RunnerProgress:
        self._validate_task_id(task_id)
        response = await self._request(
            "GET",
            f"/internal/v1/tasks/{task_id}",
            b"",
            TaskStatusResponse,
            self._inspect_timeout,
        )
        return RunnerProgress(download_stage(response.stage), response.progress)

    async def cancel(self, task_id: str) -> None:
        self._validate_task_id(task_id)
        await self._request(
            "POST",
            f"/internal/v1/tasks/{task_id}/cancel",
            CancelCommand().model_dump_json().encode(),
            CancelResponse,
            self._inspect_timeout,
        )

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def _request(
        self,
        method: str,
        target: str,
        body: bytes,
        model: type[ResponseModel],
        timeout: float,
    ) -> ResponseModel:
        timestamp, nonce = self._clock(), self._nonce()
        headers = {
            "Content-Type": "application/json",
            "X-Runner-Timestamp": str(timestamp),
            "X-Runner-Nonce": nonce,
            "X-Runner-Signature": sign_request(
                self._secret, method, target, body, timestamp, nonce
            ),
        }
        try:
            response = await self._client.request(
                method,
                target,
                content=body,
                headers=headers,
                timeout=timeout,
            )
        except httpx.HTTPError as exc:
            raise MediaRunnerClientError("runner_unavailable", 503) from exc
        if response.is_error:
            raise MediaRunnerClientError(_error_code(response), response.status_code)
        try:
            return model.model_validate_json(response.content)
        except ValidationError as exc:
            raise MediaRunnerClientError("invalid_runner_response", 502) from exc

    @staticmethod
    def _validate_task_id(task_id: str) -> None:
        if _TASK_ID.fullmatch(task_id) is None:
            raise ValueError("invalid runner task id")


def _error_code(response: httpx.Response) -> str:
    try:
        value = response.json()["error"]["code"]
    except (KeyError, TypeError, ValueError):
        return "runner_failed"
    return value if isinstance(value, str) and value else "runner_failed"
