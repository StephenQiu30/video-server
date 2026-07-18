"""Durable UTC lifecycle timestamps for PostgreSQL users."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import Engine, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from tests.integration.persistence._rights_catalog import assert_constraint
from video_server.identity.models import User

pytestmark = pytest.mark.integration

NOW = datetime(2026, 7, 18, 12, tzinfo=UTC)


def test_user_schema_requires_finite_ordered_utc_timestamps(
    migrated_database: Engine,
) -> None:
    inspector = inspect(migrated_database)
    columns = {column["name"]: column for column in inspector.get_columns("users")}
    for name in ("created_at", "updated_at"):
        assert columns[name]["nullable"] is False
        assert columns[name]["type"].timezone is True
        assert columns[name]["default"] is not None
    checks = {item["name"] for item in inspector.get_check_constraints("users")}
    assert {"ck_users_finite_times", "ck_users_time_order"} <= checks


def test_user_model_sets_and_advances_application_utc_timestamps(
    migrated_database: Engine,
) -> None:
    user = User(
        email="timestamp@example.test",
        hashed_password="$argon2id$v=19$test-only",
        is_active=True,
        is_superuser=False,
        is_verified=True,
    )
    with Session(migrated_database) as session:
        session.add(user)
        session.flush()
        assert user.created_at.tzinfo is not None
        assert user.updated_at >= user.created_at
        previous_update = user.updated_at
        user.email = "timestamp-updated@example.test"
        session.flush()
        assert user.updated_at >= previous_update
        session.rollback()


def test_user_timestamp_constraints_fail_closed(migrated_database: Engine) -> None:
    statement = text(
        """
        INSERT INTO users (
            id, email, hashed_password, is_active, is_superuser, is_verified,
            created_at, updated_at
        ) VALUES (
            :id, :email, '$argon2id$v=19$test-only', true, false, true,
            :created_at, :updated_at
        )
        """
    )
    with pytest.raises(IntegrityError) as reversed_time, migrated_database.begin() as connection:
        connection.execute(
            statement,
            {
                "id": uuid4(),
                "email": "reversed@example.test",
                "created_at": NOW,
                "updated_at": NOW - timedelta(seconds=1),
            },
        )
    assert_constraint(reversed_time.value, name="ck_users_time_order")

    with pytest.raises(IntegrityError) as infinite_time, migrated_database.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO users (
                    id, email, hashed_password, is_active, is_superuser, is_verified,
                    created_at, updated_at
                ) VALUES (
                    :id, 'infinite@example.test', '$argon2id$v=19$test-only',
                    true, false, true, 'infinity'::timestamptz, 'infinity'::timestamptz
                )
                """
            ),
            {"id": uuid4()},
        )
    assert_constraint(infinite_time.value, name="ck_users_finite_times")
