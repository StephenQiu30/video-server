from __future__ import annotations

import re
import time
from typing import Protocol

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError

from app.domain.providers import ProviderAccessContextRef
from app.runner.contracts import (
    CancelCommand,
    CancelResponse,
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
from app.runner.errors import RunnerFailure
from app.runner.provider_registry import configure_provider_instances
from app.runner.provider_sessions import ProviderSessionStore
from app.runner.readiness import RunnerReadiness
from app.runner.service import MediaRunnerService
from app.runner.settings import RunnerSettings
from app.runner.signing import (
    ExpiredSignatureError,
    HmacRequestAuthenticator,
    InMemoryNonceGuard,
    InvalidSignatureError,
    ReplayDetectedError,
    RequestAuthenticationError,
)

_TASK_ID = re.compile(r"[A-Za-z0-9_-]{1,64}")


class RunnerService(Protocol):
    async def context_for_provider(
        self, provider_key: str
    ) -> ProviderAccessContextRef: ...

    async def contexts_for_providers(
        self, provider_keys: tuple[str, ...]
    ) -> tuple[ProviderAccessContextRef, ...]: ...

    async def inspect(self, url: str) -> InspectResponse: ...

    async def download(self, request: DownloadRequest) -> DownloadResponse: ...

    async def cancel(self, task_id: str) -> CancelResponse: ...

    async def status(self, task_id: str) -> TaskStatusResponse: ...


class ReadinessProbe(Protocol):
    async def check(self) -> bool: ...


def create_app(
    settings: RunnerSettings | None = None,
    *,
    service: RunnerService | None = None,
    readiness: ReadinessProbe | None = None,
) -> FastAPI:
    configured = settings or RunnerSettings()
    configure_provider_instances(configured.peertube_allowed_instances)
    sessions = ProviderSessionStore(configured)
    runner = service or MediaRunnerService(configured, session_store=sessions)
    readiness_probe = readiness or RunnerReadiness(
        configured,
        session_ready=sessions.is_ready,
    )
    authenticator = HmacRequestAuthenticator(
        configured.hmac_secret_bytes,
        nonce_guard=InMemoryNonceGuard(
            configured.runner_nonce_ttl_seconds,
            configured.runner_nonce_max_entries,
        ),
        max_age_seconds=configured.runner_signature_max_age_seconds,
        max_future_skew_seconds=configured.runner_signature_future_skew_seconds,
    )
    app = FastAPI(title="Media Runner", docs_url=None, redoc_url=None)

    @app.exception_handler(RunnerFailure)
    async def runner_failure(_: Request, exc: RunnerFailure) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    @app.exception_handler(Exception)
    async def unexpected_failure(_: Request, __: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "internal_error", "message": "internal error"}},
        )

    @app.get("/health/live")
    async def live() -> dict[str, str]:
        return {"service": "media-runner", "status": "live"}

    @app.get("/health/ready")
    async def ready() -> JSONResponse:
        if not await readiness_probe.check():
            return JSONResponse(
                status_code=503,
                content={"service": "media-runner", "status": "unavailable"},
            )
        return JSONResponse(content={"service": "media-runner", "status": "ready"})

    @app.post("/internal/v1/inspect", response_model=InspectResponse)
    async def inspect(request: Request) -> InspectResponse:
        body = await _authenticated_body(
            request,
            configured,
            authenticator,
        )
        payload = _parse(InspectRequest, body)
        return await runner.inspect(payload.url)

    @app.post(
        "/internal/v1/context",
        response_model=ProviderAccessContextContract,
    )
    async def context(request: Request) -> ProviderAccessContextContract:
        body = await _authenticated_body(
            request,
            configured,
            authenticator,
        )
        payload = _parse(ProviderContextRequest, body)
        return ProviderAccessContextContract.from_domain(
            await runner.context_for_provider(payload.provider_key)
        )

    @app.post(
        "/internal/v1/contexts",
        response_model=ProviderContextsResponse,
    )
    async def contexts(request: Request) -> ProviderContextsResponse:
        body = await _authenticated_body(
            request,
            configured,
            authenticator,
        )
        payload = _parse(ProviderContextsRequest, body)
        resolved = await runner.contexts_for_providers(tuple(payload.provider_keys))
        return ProviderContextsResponse(
            contexts=[
                ProviderAccessContextContract.from_domain(context)
                for context in resolved
            ]
        )

    @app.post("/internal/v1/download", response_model=DownloadResponse)
    async def download(request: Request) -> DownloadResponse:
        body = await _authenticated_body(
            request,
            configured,
            authenticator,
        )
        payload = _parse(DownloadRequest, body)
        return await runner.download(payload)

    @app.post(
        "/internal/v1/tasks/{task_id}/cancel",
        response_model=CancelResponse,
    )
    async def cancel(task_id: str, request: Request) -> CancelResponse:
        body = await _authenticated_body(
            request,
            configured,
            authenticator,
        )
        _parse(CancelCommand, body)
        if _TASK_ID.fullmatch(task_id) is None:
            raise RunnerFailure("invalid_request")
        return await runner.cancel(task_id)

    @app.get(
        "/internal/v1/tasks/{task_id}",
        response_model=TaskStatusResponse,
    )
    async def status(task_id: str, request: Request) -> TaskStatusResponse:
        body = await _authenticated_body(
            request,
            configured,
            authenticator,
        )
        if body or _TASK_ID.fullmatch(task_id) is None:
            raise RunnerFailure("invalid_request")
        return await runner.status(task_id)

    return app


async def _authenticated_body(
    request: Request,
    settings: RunnerSettings,
    authenticator: HmacRequestAuthenticator,
) -> bytes:
    if request.url.query:
        raise RunnerFailure("invalid_request")
    content_length = request.headers.get("content-length")
    if content_length is not None:
        try:
            if int(content_length) > settings.runner_max_request_bytes:
                raise RunnerFailure("request_too_large", status=413)
        except ValueError as exc:
            raise RunnerFailure("invalid_request") from exc
    body = await request.body()
    if len(body) > settings.runner_max_request_bytes:
        raise RunnerFailure("request_too_large", status=413)

    timestamp = request.headers.get("X-Runner-Timestamp")
    nonce = request.headers.get("X-Runner-Nonce")
    signature = request.headers.get("X-Runner-Signature")
    if timestamp is None or nonce is None or signature is None:
        raise RunnerFailure("authentication_required", status=401)
    try:
        parsed_timestamp = int(timestamp)
        authenticator.verify(
            request.method,
            request.url.path,
            body,
            parsed_timestamp,
            nonce,
            signature,
            now=int(time.time()),
        )
    except ReplayDetectedError as exc:
        raise RunnerFailure("request_replayed", status=401) from exc
    except ExpiredSignatureError as exc:
        raise RunnerFailure("signature_expired", status=401) from exc
    except (InvalidSignatureError, RequestAuthenticationError, ValueError) as exc:
        raise RunnerFailure("invalid_signature", status=401) from exc
    return body


def _parse[ModelT: BaseModel](model: type[ModelT], body: bytes) -> ModelT:
    try:
        return model.model_validate_json(body)
    except ValidationError as exc:
        raise RunnerFailure("invalid_request") from exc
