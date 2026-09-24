"""Audit mutation requests without retaining bodies, URLs, headers or credentials."""

import json
import logging
import re
from collections.abc import Awaitable, Callable, Coroutine
from contextvars import ContextVar
from typing import Any
from uuid import UUID

from fastapi import Request
from fastapi.routing import APIRoute, iter_route_contexts
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


async def record_operation(
    request: Request,
    handler: Callable[[Request], Awaitable[Response]],
    *,
    operation: str,
    description: str,
    route: str,
) -> Response:
    store = getattr(request.app.state.services, "operation_log_store", None)
    if store is None:
        return await handler(request)
    resource_id = next(
        (value for value in request.path_params.values() if isinstance(value, UUID)),
        None,
    )
    if resource_id is None:
        for value in request.path_params.values():
            try:
                resource_id = UUID(str(value))
                break
            except ValueError:
                continue
    # A failed initial write prevents the mutation. A crash thereafter leaves a
    # durable 'started' record, never a fabricated success or automatic replay.
    entry_id = await store.begin(
        operation=operation,
        description=description,
        method=request.method,
        route=route,
        resource_id=resource_id,
    )
    resource_key = None
    status_code = None
    failed = True
    error_code = None
    token = _operation_request.set(request)
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
        _operation_request.reset(token)
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
                entry_id,
                actor=actor if isinstance(actor, CurrentUser) else None,
                status_code=status_code,
                failed=failed,
                error_code=error_code,
                resource_id=resource_id,
                resource_key=resource_key,
            )
        except Exception:
            # Keep the durable unfinished record and do not induce replay of an
            # already committed business action. Never log exception payloads.
            logger.error("operation_log_finalization_failed entry_id=%s", entry_id)


class OperationLogRoute(APIRoute):
    def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        handler = super().get_route_handler()

        async def audited(request: Request) -> Response:
            if request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
                return await handler(request)
            return await record_operation(
                request,
                handler,
                operation=self.operation_id or self.name,
                description=self.summary or self.name,
                route=next(
                    context.path
                    for context in iter_route_contexts(request.app.routes)
                    if context.original_route is self and context.path is not None
                ),
            )

        return audited
