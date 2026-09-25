"""Audit mutation requests without retaining bodies, URLs, headers or credentials."""

import inspect
import json
import logging
import re
from collections.abc import Callable, Coroutine
from contextvars import ContextVar
from dataclasses import dataclass
from functools import wraps
from typing import Any
from uuid import UUID
from weakref import WeakKeyDictionary

from fastapi import Request
from fastapi.routing import APIRoute, iter_route_contexts
from starlette.concurrency import run_in_threadpool
from starlette.responses import Response

from app.services.auth.models import CurrentUser

logger = logging.getLogger(__name__)
_operation_request: ContextVar[Request | None] = ContextVar(
    "operation_request", default=None
)


def identify_operation_actor(user: CurrentUser) -> None:
    request = _operation_request.get()
    if request is not None:
        request.state.operation_actor = user


@dataclass(slots=True)
class _PendingOperation:
    store: Any
    request: Request
    operation: str
    description: str
    route: str
    resource_id: UUID | None
    entry_id: UUID | None = None


_pending_operation: ContextVar[_PendingOperation | None] = ContextVar(
    "pending_operation", default=None
)


def _path_resource_id(request: Request) -> UUID | None:
    values = request.path_params.values()
    found = next((value for value in values if isinstance(value, UUID)), None)
    if found is not None:
        return found
    for value in values:
        try:
            return UUID(str(value))
        except ValueError:
            continue
    return None


def _begin_before_execution(
    endpoint: Callable[..., Any],
) -> Callable[..., Coroutine[Any, Any, Any]]:
    """Persist 'started' after authentication and validation, before the body.

    Requests rejected by dependencies or validation never execute a business
    operation, so they must not cost an audit write (anonymous amplification).
    """

    @wraps(endpoint)
    async def audited_endpoint(**values: Any) -> Any:
        pending = _pending_operation.get()
        if pending is not None and pending.entry_id is None:
            # A failed initial write prevents the mutation. A crash thereafter
            # leaves a durable 'started' record, never a fabricated success.
            pending.entry_id = await pending.store.begin(
                operation=pending.operation,
                description=pending.description,
                method=pending.request.method,
                route=pending.route,
                resource_id=pending.resource_id,
            )
        if inspect.iscoroutinefunction(endpoint):
            return await endpoint(**values)
        return await run_in_threadpool(endpoint, **values)

    return audited_endpoint


async def record_operation(
    request: Request,
    handler: Callable[[Request], Coroutine[Any, Any, Response]],
    *,
    operation: str,
    description: str,
    route: str,
) -> Response:
    store = getattr(request.app.state.services, "operation_log_store", None)
    if store is None:
        return await handler(request)
    pending = _PendingOperation(
        store, request, operation, description, route, _path_resource_id(request)
    )
    resource_id = pending.resource_id
    resource_key = None
    status_code = None
    failed = True
    error_code = None
    request_token = _operation_request.set(request)
    pending_token = _pending_operation.set(pending)
    try:
        response = await handler(request)
        status_code = response.status_code
        failed = status_code >= 400
        # Extract only a UUID from the already serialized response, never store
        # the response body (which may contain credentials or signed URLs).
        body = getattr(response, "body", b"")
        if resource_id is None and len(body) <= 1_048_576:
            try:
                data = json.loads(body).get("data", {})
                if isinstance(data, dict):
                    value = (
                        data.get("id") or data.get("job_id") or data.get("document_id")
                    )
                    resource_id = UUID(str(value)) if value else None
                    key = data.get("key")
                    if isinstance(key, str) and re.fullmatch(
                        r"[a-z][a-z0-9_-]{0,127}", key
                    ):
                        resource_key = key
            except (ValueError, AttributeError, TypeError):
                pass
        return response
    except Exception as exc:
        status_code = getattr(exc, "status_code", getattr(exc, "status", None))
        code = str(getattr(exc, "code", "request_failed"))
        error_code = (
            code if re.fullmatch(r"[a-zA-Z0-9_.-]{1,128}", code) else "request_failed"
        )
        raise
    finally:
        _pending_operation.reset(pending_token)
        _operation_request.reset(request_token)
        if pending.entry_id is not None:
            actor = getattr(request.state, "operation_actor", None)
            key = request.path_params.get("provider_key")
            if (
                isinstance(actor, CurrentUser)
                and actor.is_admin
                and isinstance(key, str)
                and re.fullmatch(r"[a-z][a-z0-9_-]{0,127}", key)
            ):
                resource_key = key
            try:
                await store.finish(
                    pending.entry_id,
                    actor=actor if isinstance(actor, CurrentUser) else None,
                    status_code=status_code,
                    failed=failed,
                    error_code=error_code,
                    resource_id=resource_id,
                    resource_key=resource_key,
                )
            except Exception:
                # Keep the durable unfinished record and do not induce replay of
                # an already committed business action. Never log payloads.
                logger.error(
                    "operation_log_finalization_failed entry_id=%s", pending.entry_id
                )


class OperationLogRoute(APIRoute):
    def __init__(self, path: str, endpoint: Callable[..., Any], **kwargs: Any) -> None:
        super().__init__(path, _begin_before_execution(endpoint), **kwargs)

    def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        handler = super().get_route_handler()
        # Included routers keep the unprefixed original route, so the public
        # template is resolved once per application rather than per request.
        paths: WeakKeyDictionary[Any, str] = WeakKeyDictionary()

        def public_path(request: Request) -> str:
            path = paths.get(request.app)
            if path is None:
                path = next(
                    (
                        context.path
                        for context in iter_route_contexts(request.app.routes)
                        if context.original_route is self and context.path is not None
                    ),
                    self.path,
                )
                paths[request.app] = path
            return path

        async def audited(request: Request) -> Response:
            if request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
                return await handler(request)
            return await record_operation(
                request,
                handler,
                operation=self.operation_id or self.name,
                description=self.summary or self.name,
                route=public_path(request),
            )

        return audited
