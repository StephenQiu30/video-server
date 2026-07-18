"""Scoped Alembic metadata drift detection for ORM-managed identity tables."""

from __future__ import annotations

from collections.abc import Callable

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import Engine

import video_server.persistence.base as persistence_metadata
from video_server.identity.models import AccessToken, User

pytestmark = pytest.mark.integration


def _include_object() -> Callable[..., bool]:
    function = getattr(persistence_metadata, "include_managed_object", None)
    if function is None:
        pytest.skip("the metadata-scope public contract is covered by the Red test")
    assert callable(function)
    return function


def test_persistence_base_exposes_a_metadata_scope() -> None:
    assert hasattr(persistence_metadata, "include_managed_object")


def test_identity_metadata_has_no_destructive_or_schema_drift(
    migrated_database: Engine,
) -> None:
    assert {User.__table__.name, AccessToken.__table__.name} == {"users", "access_tokens"}
    with migrated_database.connect() as connection:
        context = MigrationContext.configure(
            connection,
            opts={"include_object": _include_object()},
        )
        assert compare_metadata(context, persistence_metadata.Base.metadata) == []
