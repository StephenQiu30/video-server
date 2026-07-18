"""Authenticated UUID principal contract for domain commands."""

from __future__ import annotations

from dataclasses import fields
from types import SimpleNamespace

import pytest

from tests.identity_contract import USER_ID, make_principal, principal_type
from video_server.job.idempotency import ResolutionRequest
from video_server.persistence.resolution_create import CreateResolutionCommand


def _request() -> ResolutionRequest:
    return ResolutionRequest(
        url="https://media.example/video",
        rights_confirmed=True,
        rights_statement_version="rights-2026-07-18.1",
        rights_statement_locale="zh-CN",
    )


def test_principal_requires_a_uuid_user_id() -> None:
    principal_class = principal_type()
    principal = principal_class(user_id=USER_ID)

    assert principal.user_id == USER_ID
    for invalid in (str(USER_ID), 1, None, object()):
        with pytest.raises(TypeError):
            principal_class(user_id=invalid)


def test_resolution_command_accepts_principal_instead_of_owner_id() -> None:
    assert {item.name for item in fields(CreateResolutionCommand)} == {
        "principal",
        "idempotency_key",
        "request",
    }
    principal = make_principal(USER_ID)

    command = CreateResolutionCommand(
        principal=principal,
        idempotency_key="resolve-20260718-0001",
        request=_request(),
    )

    assert command.principal is principal


def test_resolution_command_rejects_principal_shaped_objects() -> None:
    principal_type()
    with pytest.raises(TypeError):
        CreateResolutionCommand(
            principal=SimpleNamespace(user_id=USER_ID),
            idempotency_key="resolve-20260718-0001",
            request=_request(),
        )
