"""Typed JSON envelopes applied before FastAPI response validation."""

from __future__ import annotations

import inspect
from collections.abc import Callable
from functools import wraps
from typing import Any

from fastapi.datastructures import DefaultPlaceholder
from fastapi.dependencies.utils import get_typed_return_annotation
from fastapi.routing import APIRoute
from starlette.concurrency import run_in_threadpool
from starlette.responses import Response

from app.schemas.response import ApiResponse


class ApiResponseRoute(APIRoute):
    def __init__(self, path: str, endpoint: Callable[..., Any], **kwargs: Any) -> None:
        model = kwargs.get("response_model")
        if isinstance(model, DefaultPlaceholder):
            model = get_typed_return_annotation(endpoint)
        status = kwargs.get("status_code") or 200
        if (
            model is not None
            and status not in (204, 304)
            and not (inspect.isclass(model) and issubclass(model, Response))
            and not getattr(endpoint, "__api_enveloped__", False)
        ):
            original = endpoint

            @wraps(original)
            async def enveloped(**values: Any) -> Any:
                result = (
                    await original(**values)
                    if inspect.iscoroutinefunction(original)
                    else await run_in_threadpool(original, **values)
                )
                if isinstance(result, Response):
                    return result
                return {"code": "ok", "message": "OK", "data": result}

            enveloped.__api_enveloped__ = True  # type: ignore[attr-defined]
            endpoint = enveloped
            kwargs["response_model"] = ApiResponse[model]  # type: ignore[valid-type]
        super().__init__(path, endpoint, **kwargs)
