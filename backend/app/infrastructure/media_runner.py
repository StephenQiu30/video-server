"""HMAC-authenticated client for the isolated Media Runner service."""

from __future__ import annotations

import asyncio
import math
import re
import secrets
import time
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Protocol, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from app.application.downloads import (
    MediaInspectionFailure,
    RunnerFormat,
    RunnerInspection,
)
from app.application.downloads.errors import (
    MediaInspectionAuthRequired,
    MediaInspectionContentRestricted,
    MediaInspectionDrmProtected,
    MediaInspectionDurationLimitExceeded,
    MediaInspectionFormatUnavailable,
    MediaInspectionGeoRestricted,
    MediaInspectionLinkUnavailable,
    MediaInspectionMediaUnsupported,
    MediaInspectionRateLimited,
    MediaInspectionSessionExpired,
    MediaInspectionTemporarilyUnavailable,
    MediaInspectionTimeout,
    MediaInspectionUnsupported,
    MediaInspectionVerificationFailed,
)
from app.domain.downloads import DownloadPlan
from app.domain.providers import ProviderAccessContextRef, ProviderAccessMode
from app.infrastructure.media_inspection_pipeline import MediaInspectionPipeline
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
    ProviderAccessContextContract,
    ProviderContextRequest,
    ProviderContextsRequest,
    ProviderContextsResponse,
    TaskStatusResponse,
)
from app.runner.provider_registry import provider_profile
from app.runner.signing import sign_request

_TASK_ID = re.compile(r"[A-Za-z0-9_-]{1,64}")
_CONTEXT_TIMEOUT_SECONDS = 2.0
_STATUS_CONTEXT_TIMEOUT_SECONDS = 0.25
ResponseModel = TypeVar("ResponseModel", bound=BaseModel)


class MediaRunnerClient(Protocol):
    """Runner strategy used by the routing facade."""

    async def context(self, url: str) -> ProviderAccessContextRef: ...

    async def context_for_provider(
        self, provider_key: str
    ) -> ProviderAccessContextRef: ...

    async def contexts_for_providers(
        self, provider_keys: tuple[str, ...]
    ) -> tuple[ProviderAccessContextRef, ...]: ...

    async def inspect(self, url: str) -> RunnerInspection: ...

    async def download(
        self,
        task_id: str,
        url: str,
        plan: DownloadPlan,
        *,
        expected_provider_media_id: str,
        expected_extractor_key: str,
        access_context: ProviderAccessContextRef,
    ) -> RunnerArtifact: ...

    async def status(self, task_id: str) -> RunnerProgress: ...

    async def cancel(self, task_id: str) -> None: ...

    async def close(self) -> None: ...


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

    async def context(self, url: str) -> ProviderAccessContextRef:
        return await self.context_for_provider(provider_profile(url).key)

    async def context_for_provider(self, provider_key: str) -> ProviderAccessContextRef:
        response = await self._request(
            "POST",
            "/internal/v1/context",
            ProviderContextRequest(provider_key=provider_key)
            .model_dump_json()
            .encode(),
            ProviderAccessContextContract,
            min(self._inspect_timeout, _CONTEXT_TIMEOUT_SECONDS),
            timeout_code="inspection_timeout",
        )
        return _context_to_domain(response)

    async def contexts_for_providers(
        self, provider_keys: tuple[str, ...]
    ) -> tuple[ProviderAccessContextRef, ...]:
        response = await self._request(
            "POST",
            "/internal/v1/contexts",
            ProviderContextsRequest(provider_keys=list(provider_keys))
            .model_dump_json()
            .encode(),
            ProviderContextsResponse,
            min(self._inspect_timeout, _STATUS_CONTEXT_TIMEOUT_SECONDS),
            timeout_code="inspection_timeout",
        )
        return tuple(_context_to_domain(context) for context in response.contexts)

    async def inspect(self, url: str) -> RunnerInspection:
        try:
            response = await self._request(
                "POST",
                "/internal/v1/inspect",
                InspectRequest(url=url).model_dump_json().encode(),
                InspectResponse,
                self._inspect_timeout,
                timeout_code="inspection_timeout",
            )
        except MediaRunnerClientError as exc:
            if exc.code == "duration_limit_exceeded":
                raise MediaInspectionDurationLimitExceeded from exc
            if exc.code in {"credential_required", "provider_session_not_allowed"}:
                raise MediaInspectionAuthRequired from exc
            if exc.code in {
                "credential_expired",
                "credential_rejected",
                "credential_revoked",
            }:
                raise MediaInspectionSessionExpired from exc
            if exc.code in {
                "egress_challenged",
                "pot_required",
                "pot_rejected",
                "client_context_mismatch",
            }:
                raise MediaInspectionVerificationFailed from exc
            if exc.code == "provider_rate_limited":
                raise MediaInspectionRateLimited from exc
            if exc.code == "provider_geo_restricted":
                raise MediaInspectionGeoRestricted from exc
            if exc.code in {
                "content_private",
                "content_not_entitled",
                "content_entitlement_unknown",
            }:
                raise MediaInspectionContentRestricted from exc
            if exc.code == "drm_protected":
                raise MediaInspectionDrmProtected from exc
            if exc.code in {
                "pot_provider_unavailable",
                "extractor_regression",
                "provider_temporarily_unavailable",
                "provider_session_unavailable",
            }:
                raise MediaInspectionTemporarilyUnavailable from exc
            if exc.code == "provider_link_unavailable":
                raise MediaInspectionLinkUnavailable from exc
            if exc.code == "provider_media_unsupported":
                raise MediaInspectionMediaUnsupported from exc
            if exc.code == "format_unavailable":
                raise MediaInspectionFormatUnavailable from exc
            if exc.code == "provider_unsupported":
                raise MediaInspectionUnsupported from exc
            if exc.code == "inspection_timeout":
                raise MediaInspectionTimeout from exc
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
            access_context=response.access_context.to_domain(),
            thumbnail_data_url=response.media.thumbnail_data_url,
        )

    async def download(
        self,
        task_id: str,
        url: str,
        plan: DownloadPlan,
        *,
        expected_provider_media_id: str,
        expected_extractor_key: str,
        access_context: ProviderAccessContextRef,
    ) -> RunnerArtifact:
        self._validate_task_id(task_id)
        body = (
            DownloadRequest(
                task_id=task_id,
                url=url,
                expected_provider_media_id=expected_provider_media_id,
                expected_extractor_key=expected_extractor_key,
                plan=DownloadPlanContract.from_domain(plan),
                access_context=ProviderAccessContextContract.from_domain(
                    access_context
                ),
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
            timeout_code="download_timeout",
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
            timeout_code="runner_unavailable",
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
            timeout_code="runner_unavailable",
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
        *,
        timeout_code: str,
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
        except httpx.TimeoutException as exc:
            raise MediaRunnerClientError(timeout_code, 504) from exc
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


class MediaRunnerRouter:
    """Route anonymous and operator contexts to physically separate runners."""

    def __init__(
        self,
        anonymous: MediaRunnerClient,
        operators: Mapping[str, MediaRunnerClient] | None = None,
    ) -> None:
        self._anonymous = anonymous
        self._operators = dict(operators or {})
        self._inspection_pipeline = MediaInspectionPipeline(
            anonymous,
            self._operators,
        )
        self._active: dict[str, MediaRunnerClient] = {}

    async def inspect(self, url: str) -> RunnerInspection:
        return await self._inspection_pipeline.inspect(url)

    async def context_for_provider(
        self,
        provider_key: str,
        access_mode: ProviderAccessMode,
    ) -> ProviderAccessContextRef:
        client = (
            self._anonymous
            if access_mode is ProviderAccessMode.ANONYMOUS
            else self._operators.get(provider_key)
        )
        if client is None:
            raise MediaRunnerClientError("credential_required", 422)
        context = await client.context_for_provider(provider_key)
        if context.access_mode is not access_mode:
            raise MediaRunnerClientError("client_context_mismatch", 502)
        return context

    async def contexts_for_providers(
        self,
        requested: Mapping[str, ProviderAccessMode],
    ) -> Mapping[str, ProviderAccessContextRef]:
        anonymous_keys = tuple(
            key
            for key, mode in requested.items()
            if mode is ProviderAccessMode.ANONYMOUS
        )
        groups: list[tuple[MediaRunnerClient, tuple[str, ...]]] = []
        if anonymous_keys:
            groups.append((self._anonymous, anonymous_keys))
        groups.extend(
            (client, (key,))
            for key, mode in requested.items()
            if mode is ProviderAccessMode.OPERATOR_MANAGED
            and (client := self._operators.get(key)) is not None
        )

        async def resolve(
            client: MediaRunnerClient,
            keys: tuple[str, ...],
        ) -> tuple[ProviderAccessContextRef, ...]:
            try:
                return await client.contexts_for_providers(keys)
            except MediaRunnerClientError:
                return ()

        batches = await asyncio.gather(
            *(resolve(client, keys) for client, keys in groups)
        )
        contexts = {
            context.provider_key: context
            for batch in batches
            for context in batch
            if requested.get(context.provider_key) is context.access_mode
        }
        return contexts

    async def download(
        self,
        task_id: str,
        url: str,
        plan: DownloadPlan,
        *,
        expected_provider_media_id: str,
        expected_extractor_key: str,
        access_context: ProviderAccessContextRef,
    ) -> RunnerArtifact:
        client = self._client_for(access_context)
        self._active[task_id] = client
        try:
            return await client.download(
                task_id,
                url,
                plan,
                expected_provider_media_id=expected_provider_media_id,
                expected_extractor_key=expected_extractor_key,
                access_context=access_context,
            )
        finally:
            self._active.pop(task_id, None)

    async def status(self, task_id: str) -> RunnerProgress:
        return await self._active.get(task_id, self._anonymous).status(task_id)

    async def cancel(self, task_id: str) -> None:
        await self._active.get(task_id, self._anonymous).cancel(task_id)

    async def close(self) -> None:
        await self._anonymous.close()
        for operator in self._operators.values():
            await operator.close()

    def _client_for(self, context: ProviderAccessContextRef) -> MediaRunnerClient:
        if context.access_mode is ProviderAccessMode.ANONYMOUS:
            return self._anonymous
        if context.access_mode is ProviderAccessMode.OPERATOR_MANAGED:
            operator = self._operators.get(context.provider_key)
            if operator is not None:
                return operator
        raise MediaRunnerClientError("credential_required", 422)


def _error_code(response: httpx.Response) -> str:
    try:
        value = response.json()["error"]["code"]
    except (KeyError, TypeError, ValueError):
        return "runner_failed"
    return value if isinstance(value, str) and value else "runner_failed"


def _context_to_domain(
    contract: ProviderAccessContextContract,
) -> ProviderAccessContextRef:
    try:
        return contract.to_domain()
    except ValueError as exc:
        raise MediaRunnerClientError("invalid_runner_response", 502) from exc
