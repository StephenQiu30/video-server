from __future__ import annotations

from collections.abc import Callable

import pytest

from video_server.errors import DomainError
from video_server.security.request_gate import InstallationPrincipal, RequestContext, RequestGate

OWNER_ID = "installation-01"
TOKEN = "install-token-0123456789"
WEB_ORIGIN = "http://127.0.0.1:3000"
API_AUTHORITY = "127.0.0.1:8000"
CONTROL_CHARACTERS = tuple(chr(code) for code in (*range(0x20), 0x7F))


def _gate(token: str = TOKEN) -> RequestGate:
    return RequestGate(
        InstallationPrincipal(owner_id=OWNER_ID, bearer_token=token),
        web_origin=WEB_ORIGIN,
        api_authority=API_AUTHORITY,
    )


def _post(*, content_type: str, authorization: str | None = None) -> RequestContext:
    return RequestContext(
        method="POST",
        authority=API_AUTHORITY,
        authorization=authorization or f"Bearer {TOKEN}",
        origin=WEB_ORIGIN,
        fetch_site="same-origin",
        content_type=content_type,
    )


def _assert_error(expected_code: str, operation: Callable[[], object]) -> DomainError:
    with pytest.raises(DomainError) as caught:
        operation()
    assert caught.value.code == expected_code
    assert caught.value.retryable is False
    return caught.value


@pytest.mark.parametrize(
    "content_type",
    [
        "application/json",
        "Application/Json; Charset=UTF-8",
        "application/json ; charset = utf-8",
    ],
)
def test_valid_application_json_values_remain_accepted(content_type: str) -> None:
    assert _gate().authorize(_post(content_type=content_type)) == OWNER_ID


def test_joined_duplicate_content_type_is_rejected() -> None:
    _assert_error(
        "CONTENT_TYPE_UNSUPPORTED",
        lambda: _gate().authorize(
            _post(content_type="application/json; charset=utf-8, text/plain")
        ),
    )


@pytest.mark.parametrize("control", CONTROL_CHARACTERS)
def test_content_type_rejects_every_control_character(control: str) -> None:
    _assert_error(
        "CONTENT_TYPE_UNSUPPORTED",
        lambda: _gate().authorize(_post(content_type=f"application/json; charset=utf{control}8")),
    )


def test_content_type_rejects_crlf_header_injection() -> None:
    _assert_error(
        "CONTENT_TYPE_UNSUPPORTED",
        lambda: _gate().authorize(
            _post(content_type="application/json; charset=utf-8\r\nContent-Type: text/plain")
        ),
    )


@pytest.mark.parametrize(
    "content_type",
    [
        "application/json; =utf-8",
        "application/json; char set=utf-8",
        "application/json; charset@=utf-8",
        "application/json; charset=utf-8; charset=utf-16",
        "application/json; Charset=utf-8; CHARSET=utf-16",
    ],
)
def test_content_type_rejects_invalid_or_duplicate_parameter_names(content_type: str) -> None:
    _assert_error(
        "CONTENT_TYPE_UNSUPPORTED",
        lambda: _gate().authorize(_post(content_type=content_type)),
    )


@pytest.mark.parametrize(
    "presented_token",
    ["café", "秘密", *(f"left{control}right" for control in CONTROL_CHARACTERS)],
)
def test_malformed_presented_bearer_has_a_stable_safe_error(presented_token: str) -> None:
    authorization = f"Bearer {presented_token}"

    error = _assert_error(
        "AUTHENTICATION_REQUIRED",
        lambda: _gate().authorize(
            _post(content_type="application/json", authorization=authorization)
        ),
    )

    assert TOKEN not in error.detail
    assert presented_token not in error.detail


@pytest.mark.parametrize(
    "configured_token",
    [
        "café",
        "秘密",
        "token,other",
        " token",
        "token ",
        "token value",
        *(f"left{control}right" for control in CONTROL_CHARACTERS),
    ],
)
def test_installation_token_rejects_non_ascii_separators_and_controls(
    configured_token: str,
) -> None:
    error = _assert_error(
        "AUTHENTICATION_REQUIRED",
        lambda: _gate(configured_token),
    )

    assert configured_token not in error.detail
