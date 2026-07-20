from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import Response
from fastapi.exceptions import RequestValidationError
from src.api.v1.health import get_liveness, get_readiness
from src.core.errors import (
    AppError,
    app_error_handler,
    http_exception_handler,
    problem_response,
    request_validation_error_handler,
    unhandled_exception_handler,
)
from src.core.security import (
    create_session_token,
    hash_session_token,
    is_allowed_origin,
    redact_url,
    require_same_origin,
    require_session_token,
    safe_headers,
    session_token_from_request,
)
from starlette.exceptions import HTTPException
from starlette.requests import Request


def request(
    headers: list[tuple[bytes, bytes]] | None = None,
    cookies: dict[str, str] | None = None,
) -> Request:
    if cookies:
        headers = list(headers or []) + [
            (
                b"cookie",
                "; ".join(f"{key}={value}" for key, value in cookies.items()).encode(),
            )
        ]
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": headers or [],
        "query_string": b"",
        "scheme": "https",
        "server": ("testserver", 443),
        "client": ("127.0.0.1", 1234),
    }
    result = Request(scope)
    return result


def cfg() -> SimpleNamespace:
    return SimpleNamespace(
        session_cookie_name="video_session",
        session_ttl_seconds=60,
        web_origin="https://example.test",
    )


def test_security_origin_cookie_and_headers() -> None:
    token = create_session_token()
    assert len(token) >= 40
    assert len(hash_session_token(token)) == 64
    with pytest.raises(ValueError):
        hash_session_token("")
    assert is_allowed_origin("https://example.test/", "https://example.test")
    assert not is_allowed_origin("https://example.test/path", "https://example.test")
    assert not is_allowed_origin(None, "https://example.test")
    assert redact_url("not a url") == "[redacted-url]"
    assert redact_url("https://[bad") == "[redacted-url]"
    headers = safe_headers(
        {"Authorization": "secret", "X-Trace": "ok", "Cookie": "secret"}
    )
    assert headers == {"authorization": "***", "x-trace": "ok", "cookie": "***"}

    req = request(cookies={"video_session": "token"})
    assert session_token_from_request(req, cfg()) == "token"
    assert require_session_token(req, cfg()) == "token"
    with pytest.raises(AppError):
        require_session_token(request(), cfg())
    require_same_origin(request([(b"origin", b"https://example.test")]), cfg())
    with pytest.raises(AppError):
        require_same_origin(request([(b"origin", b"https://evil.test")]), cfg())


@pytest.mark.asyncio
async def test_problem_handlers_redact_and_keep_content_type() -> None:
    response = problem_response(
        status_code=422,
        code="BAD_INPUT",
        detail="invalid",
        details={"fields": ["url"], "secret": "never"},
    )
    assert response.media_type == "application/problem+json"
    assert response.body is not None and b"never" not in response.body
    app_response = await app_error_handler(
        request(), AppError("BAD", "bad", status_code=409)
    )
    assert app_response.status_code == 409
    validation = RequestValidationError(
        [{"type": "missing", "loc": ("body", "url"), "msg": "required", "input": None}]
    )
    validation_response = await request_validation_error_handler(request(), validation)
    assert validation_response.status_code == 400
    assert b"body.url" in validation_response.body
    http_response = await http_exception_handler(
        request(), HTTPException(status_code=404, detail="missing")
    )
    assert http_response.status_code == 404
    internal = await unhandled_exception_handler(request(), RuntimeError("secret"))
    assert internal.status_code == 500 and b"secret" not in (internal.body or b"")


@pytest.mark.asyncio
async def test_readiness_shapes_and_failure() -> None:
    assert await get_liveness() == {"status": "ok"}
    response = Response()
    result = await get_readiness(request(), response, None)
    assert response.status_code == 503 and result["status"] == "not_ready"
    response = Response()
    assert await get_readiness(request(), response, lambda: True) == {"status": "ok"}
    response = Response()
    assert (await get_readiness(request(), response, lambda: False))[
        "status"
    ] == "not_ready"
    assert response.status_code == 503
    response = Response()
    assert await get_readiness(request(), response, lambda: {"status": "ready"}) == {
        "status": "ready"
    }
    response = Response()
    assert await get_readiness(request(), response, lambda: "unknown") == {
        "status": "ok"
    }
    with pytest.raises(AppError):
        await get_readiness(
            request(), Response(), lambda: (_ for _ in ()).throw(RuntimeError("down"))
        )
