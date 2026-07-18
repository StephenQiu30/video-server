"""Test-side contract helpers for the authenticated principal boundary."""

from __future__ import annotations

from dataclasses import fields
from typing import get_type_hints
from uuid import UUID

from video_server.persistence.resolution_create import CreateResolutionCommand

USER_ID = UUID("8f83e1c4-9a31-4c26-b2de-9a7f53dd6ed1")
OTHER_USER_ID = UUID("73dd389a-467e-49cd-9fd2-3e5d9d8aa9bb")


def principal_type() -> type[object]:
    """Resolve Principal through the existing command without importing a future module."""

    command_fields = {item.name for item in fields(CreateResolutionCommand)}
    assert command_fields == {"principal", "idempotency_key", "request"}
    annotation = get_type_hints(CreateResolutionCommand)["principal"]
    assert isinstance(annotation, type)
    return annotation


def make_principal(user_id: UUID) -> object:
    """Build the exact Principal type accepted by CreateResolutionCommand."""

    return principal_type()(user_id=user_id)
