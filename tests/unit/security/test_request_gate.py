from __future__ import annotations

import hmac
import secrets
from collections.abc import Callable

import pytest

import video_server.security.request_gate as request_gate_module
from video_server.errors import DomainError
from video_server.security.request_gate import InstallationPrincipal, RequestContext, RequestGate

OWNER_ID = "installation-01"
TOKEN = "install-token-0123456789"
WEB_ORIGIN = "http://127.0.0.1:3000"
API_AUTHORITY = "127.0.0.1:8000"
METHODS = ("GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS")


def _gate() -> RequestGate:
    return RequestGate(
        InstallationPrincipal(owner_id=OWNER_ID, bearer_token=TOKEN),
        web_origin=WEB_ORIGIN,
        api_authority=API_AUTHORITY,
    )


def _context(method: str = "GET", **changes: str | None) -> RequestContext:
    values: dict[str, str | None] = {
        "authority": API_AUTHORITY,
        "authorization": f"Bearer {TOKEN}",
        "origin": WEB_ORIGIN,
        "fetch_site": "same-origin",
        "content_type": "application/json" if method in METHODS[2:6] else None,
    }
    values.update(changes)
    return RequestContext(method=method, **values)


def _assert_code(expected: str, operation: Callable[[], object]) -> DomainError:
    with pytest.raises(DomainError) as caught:
        operation()
    assert caught.value.code == expected
    assert caught.value.retryable is False
    return caught.value


@pytest.mark.parametrize("field", ["owner_id", "bearer_token"])
@pytest.mark.parametrize("invalid", ["", "   "])
def test_principal_requires_nonempty_owner_and_token(field: str, invalid: str) -> None:
    values = {"owner_id": OWNER_ID, "bearer_token": TOKEN, field: invalid}

    error = _assert_code(
        "AUTHENTICATION_REQUIRED",
        lambda: RequestGate(
            InstallationPrincipal(**values),
            web_origin=WEB_ORIGIN,
            api_authority=API_AUTHORITY,
        ),
    )

    assert TOKEN not in str(error)
    assert TOKEN not in error.detail


@pytest.mark.parametrize(
    ("web_origin", "api_authority"),
    [
        ("", API_AUTHORITY),
        (" ", API_AUTHORITY),
        ("https://127.0.0.1:3000", API_AUTHORITY),
        ("http://example.com:3000", API_AUTHORITY),
        ("http://127.0.0.1:3000/", API_AUTHORITY),
        (WEB_ORIGIN, ""),
        (WEB_ORIGIN, " "),
        (WEB_ORIGIN, "http://127.0.0.1:8000"),
        (WEB_ORIGIN, "127.0.0.1:8000/path"),
        (WEB_ORIGIN, "example.com:8000"),
        (WEB_ORIGIN, "LOCALHOST:8000"),
    ],
)
def test_gate_requires_exact_http_loopback_configuration(
    web_origin: str,
    api_authority: str,
) -> None:
    _assert_code(
        "REQUEST_ORIGIN_REJECTED",
        lambda: RequestGate(
            InstallationPrincipal(OWNER_ID, TOKEN),
            web_origin=web_origin,
            api_authority=api_authority,
        ),
    )


@pytest.mark.parametrize("method", METHODS)
def test_every_method_requires_exact_authority_origin_and_fetch_site(method: str) -> None:
    gate = _gate()

    for changes in (
        {"authority": None},
        {"authority": f"{API_AUTHORITY}, {API_AUTHORITY}"},
        {"authority": f" {API_AUTHORITY}"},
        {"origin": None},
        {"origin": "HTTP://127.0.0.1:3000"},
        {"origin": f"{WEB_ORIGIN} "},
        {"fetch_site": None},
        {"fetch_site": "Same-Origin"},
        {"fetch_site": "same-site"},
    ):
        _assert_code(
            "REQUEST_ORIGIN_REJECTED",
            lambda changes=changes: gate.authorize(_context(method, **changes)),
        )


@pytest.mark.parametrize(
    "authorization",
    [
        None,
        "",
        TOKEN,
        f"bearer {TOKEN}",
        f"Bearer  {TOKEN}",
        f" Bearer {TOKEN}",
        f"Bearer {TOKEN} ",
        f"Bearer {TOKEN}, Bearer {TOKEN}",
        "Basic install-token-0123456789",
        "Bearer install-token-xxxxxxxxxx",
    ],
)
def test_bearer_header_is_exact_and_never_leaked(authorization: str | None) -> None:
    error = _assert_code(
        "AUTHENTICATION_REQUIRED",
        lambda: _gate().authorize(_context(authorization=authorization)),
    )

    assert TOKEN not in str(error)
    assert TOKEN not in error.detail
    if authorization is not None:
        assert authorization not in error.detail


def test_bearer_token_uses_constant_time_comparison(monkeypatch: pytest.MonkeyPatch) -> None:
    real_compare = hmac.compare_digest
    compared: list[tuple[str | bytes, str | bytes]] = []

    def spy(left: str | bytes, right: str | bytes) -> bool:
        compared.append((left, right))
        return real_compare(left, right)

    monkeypatch.setattr(hmac, "compare_digest", spy)
    monkeypatch.setattr(secrets, "compare_digest", spy)
    if hasattr(request_gate_module, "compare_digest"):
        monkeypatch.setattr(request_gate_module, "compare_digest", spy)

    assert _gate().authorize(_context()) == OWNER_ID
    assert compared
    assert any(TOKEN in pair for pair in compared)


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
@pytest.mark.parametrize(
    "content_type",
    ["application/json", "Application/Json; Charset=UTF-8", "application/json ; charset = utf-8"],
)
def test_mutations_accept_parsed_application_json(method: str, content_type: str) -> None:
    assert _gate().authorize(_context(method, content_type=content_type)) == OWNER_ID


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
@pytest.mark.parametrize(
    "content_type",
    [
        None,
        "",
        "text/json",
        "application/jsonp",
        "application/problem+json",
        "application/json, text/plain",
    ],
)
def test_mutations_reject_non_json_content_type(method: str, content_type: str | None) -> None:
    _assert_code(
        "CONTENT_TYPE_UNSUPPORTED",
        lambda: _gate().authorize(_context(method, content_type=content_type)),
    )


@pytest.mark.parametrize("method", ["GET", "HEAD"])
@pytest.mark.parametrize("content_type", [None, "", "text/plain"])
def test_safe_reads_do_not_require_content_type(method: str, content_type: str | None) -> None:
    assert _gate().authorize(_context(method, content_type=content_type)) == OWNER_ID


def test_success_returns_only_the_owner_id() -> None:
    assert _gate().authorize(_context()) == OWNER_ID
