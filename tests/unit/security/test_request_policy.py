"""Host, origin, Fetch Metadata, and JSON policy without installation auth."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import fields

import pytest

import video_server.security as security
from video_server.errors import DomainError

WEB_ORIGIN = "http://127.0.0.1:3000"
API_AUTHORITY = "127.0.0.1:8000"
UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


def _types() -> tuple[type[object], type[object]]:
    if not all(hasattr(security, name) for name in ("RequestMetadata", "RequestPolicy")):
        pytest.skip("the public request-policy contract is covered by the Red test")
    return security.RequestMetadata, security.RequestPolicy


def _policy() -> object:
    _, policy_type = _types()
    return policy_type(
        trusted_api_authority=API_AUTHORITY,
        trusted_web_origin=WEB_ORIGIN,
    )


def _request(method: str = "GET", **changes: str | None) -> object:
    metadata_type, _ = _types()
    unsafe = method in UNSAFE_METHODS
    values: dict[str, str | None] = {
        "authority": API_AUTHORITY,
        "origin": WEB_ORIGIN if unsafe else None,
        "fetch_site": "same-origin" if unsafe else None,
        "content_type": "application/json" if unsafe else None,
    }
    values.update(changes)
    return metadata_type(method=method, **values)


def _assert_code(expected: str, operation: Callable[[], object]) -> None:
    with pytest.raises(DomainError) as caught:
        operation()
    assert caught.value.code == expected
    assert caught.value.retryable is False


def test_security_package_exposes_request_policy_contract() -> None:
    assert hasattr(security, "RequestMetadata")
    assert hasattr(security, "RequestPolicy")


def test_request_metadata_contains_no_identity_or_bearer_fields() -> None:
    metadata_type, _ = _types()
    assert {item.name for item in fields(metadata_type)} == {
        "method",
        "authority",
        "origin",
        "fetch_site",
        "content_type",
    }


@pytest.mark.parametrize("method", ["GET", "HEAD"])
def test_safe_read_requires_authority_but_not_origin_or_content_type(method: str) -> None:
    policy = _policy()
    assert policy.validate(_request(method)) is None
    _assert_code(
        "REQUEST_ORIGIN_REJECTED",
        lambda: policy.validate(_request(method, authority="example.test")),
    )


@pytest.mark.parametrize("method", sorted(UNSAFE_METHODS))
def test_unsafe_method_requires_same_origin_metadata_and_json(method: str) -> None:
    policy = _policy()
    request = _request(
        method,
        origin=WEB_ORIGIN,
        fetch_site="same-origin",
        content_type="Application/Json; Charset=UTF-8",
    )
    assert policy.validate(request) is None

    for changes in (
        {"authority": "example.test"},
        {"origin": None},
        {"origin": "https://example.test"},
        {"fetch_site": None},
        {"fetch_site": ""},
        {"fetch_site": "Same-Origin"},
        {"fetch_site": "same-origin "},
        {"fetch_site": "same-origin, same-origin"},
        {"fetch_site": "same-site"},
    ):
        _assert_code(
            "REQUEST_ORIGIN_REJECTED",
            lambda changes=changes: policy.validate(_request(method, **changes)),
        )


@pytest.mark.parametrize(
    "authority",
    [
        None,
        "",
        " ",
        f"{API_AUTHORITY}, {API_AUTHORITY}",
        f"{API_AUTHORITY},{API_AUTHORITY}",
        f" {API_AUTHORITY}",
        f"{API_AUTHORITY} ",
        f"{API_AUTHORITY}\t",
        f"http://{API_AUTHORITY}",
        "EXAMPLE.test:8000",
    ],
)
def test_host_authority_is_single_and_exact(authority: str | None) -> None:
    _assert_code(
        "REQUEST_ORIGIN_REJECTED",
        lambda: _policy().validate(_request(authority=authority)),
    )


@pytest.mark.parametrize(
    "origin",
    [
        None,
        "",
        " ",
        "HTTP://127.0.0.1:3000",
        f"{WEB_ORIGIN} ",
        f" {WEB_ORIGIN}",
        f"{WEB_ORIGIN}, {WEB_ORIGIN}",
        f"{WEB_ORIGIN}/",
        "https://example.test",
    ],
)
def test_unsafe_origin_is_single_and_exact(origin: str | None) -> None:
    _assert_code(
        "REQUEST_ORIGIN_REJECTED",
        lambda: _policy().validate(_request("POST", origin=origin)),
    )


@pytest.mark.parametrize(
    "content_type",
    [None, "", "text/json", "application/problem+json", "application/json, text/plain"],
)
def test_unsafe_method_rejects_non_json_content_type(content_type: str | None) -> None:
    policy = _policy()
    _assert_code(
        "CONTENT_TYPE_UNSUPPORTED",
        lambda: policy.validate(_request("POST", content_type=content_type)),
    )


@pytest.mark.parametrize("control", [*(chr(code) for code in range(0x20)), chr(0x7F)])
def test_json_content_type_rejects_controls(control: str) -> None:
    policy = _policy()
    _assert_code(
        "CONTENT_TYPE_UNSUPPORTED",
        lambda: policy.validate(
            _request("POST", content_type=f"application/json; charset=utf{control}8")
        ),
    )


@pytest.mark.parametrize(
    "content_type",
    [
        "application/json; =utf-8",
        "application/json; char set=utf-8",
        "application/json; charset=utf-8; charset=utf-16",
        'application/json; charset="unterminated',
    ],
)
def test_json_content_type_rejects_invalid_parameters(content_type: str) -> None:
    policy = _policy()
    _assert_code(
        "CONTENT_TYPE_UNSUPPORTED",
        lambda: policy.validate(_request("POST", content_type=content_type)),
    )
