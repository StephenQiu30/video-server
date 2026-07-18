"""FastAPI Users PostgreSQL identity and DatabaseStrategy contracts."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from importlib import import_module
from uuid import UUID

import pytest
from sqlalchemy import Engine, inspect, text, update
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session

from tests.identity_contract import OTHER_USER_ID, USER_ID
from tests.integration.persistence._identity import insert_access_token, insert_user
from tests.integration.persistence._rights_catalog import assert_constraint

pytestmark = pytest.mark.integration


def test_identity_tables_match_fastapi_users_schema(migrated_database: Engine) -> None:
    inspector = inspect(migrated_database)
    assert {"users", "access_tokens"} <= set(inspector.get_table_names())
    users = {column["name"]: column for column in inspector.get_columns("users")}
    expected = {"id", "email", "hashed_password", "is_active", "is_superuser", "is_verified"}
    assert expected <= set(users)
    assert isinstance(users["id"]["type"], PostgreSQLUUID)
    assert users["id"]["nullable"] is False
    assert users["id"]["default"] is None
    assert users["email"]["type"].length == 320
    assert users["hashed_password"]["type"].length == 1024
    assert all(users[name]["nullable"] is False for name in expected)
    assert inspector.get_pk_constraint("users")["constrained_columns"] == ["id"]
    assert _has_index(inspector, "users", "email")
    assert _has_normalized_email_unique_index(migrated_database)

    tokens = {column["name"]: column for column in inspector.get_columns("access_tokens")}
    assert set(tokens) == {"token", "created_at", "user_id"}
    assert tokens["token"]["type"].length == 43
    assert isinstance(tokens["user_id"]["type"], PostgreSQLUUID)
    assert all(column["nullable"] is False for column in tokens.values())
    assert tokens["created_at"]["type"].timezone is True
    assert inspector.get_pk_constraint("access_tokens")["constrained_columns"] == ["token"]
    assert _has_index(inspector, "access_tokens", "created_at")
    assert _user_foreign_key(inspector) == {"ondelete": "CASCADE"}


def test_email_uniqueness_is_case_insensitive(migrated_database: Engine) -> None:
    with migrated_database.begin() as connection:
        insert_user(connection, USER_ID, email="Creator@Example.test")
    with pytest.raises(IntegrityError) as rejected, migrated_database.begin() as connection:
        insert_user(connection, OTHER_USER_ID, email="creator@example.test")
    assert_constraint(rejected.value, name="uq_users_email_normalized", sqlstate="23505")


def test_user_model_generates_uuid4_outside_postgresql(migrated_database: Engine) -> None:
    assert "users" in inspect(migrated_database).get_table_names()
    user_model = import_module("video_server.identity.models").User
    user = user_model(
        email="generated@example.test",
        hashed_password="$argon2id$v=19$test-only",
        is_active=True,
        is_superuser=False,
        is_verified=True,
    )
    with Session(migrated_database) as session:
        session.add(user)
        session.flush()
        assert isinstance(user.id, UUID)
        assert user.id.version == 4
        session.rollback()


def test_access_tokens_require_and_cascade_with_uuid_user(migrated_database: Engine) -> None:
    with migrated_database.begin() as connection:
        insert_user(connection)
        insert_access_token(connection)
    with pytest.raises(IntegrityError) as rejected, migrated_database.begin() as connection:
        insert_access_token(connection, user_id=OTHER_USER_ID, token="t" * 43)
    assert_constraint(rejected.value, name="fk_access_tokens_user_id_users", sqlstate="23503")
    with migrated_database.begin() as connection:
        connection.execute(text("DELETE FROM users WHERE id=:id"), {"id": USER_ID})
    with migrated_database.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM access_tokens")) == 0


@pytest.mark.asyncio
async def test_database_strategy_round_trip_expiry_and_destroy(
    migrated_database: Engine,
    postgres_url: str,
) -> None:
    assert "access_tokens" in inspect(migrated_database).get_table_names()
    models = import_module("video_server.identity.models")
    sessions = import_module("video_server.identity.sessions")
    adapter = import_module("fastapi_users_db_sqlalchemy.access_token")
    async_engine = create_async_engine(postgres_url)
    factory = async_sessionmaker(async_engine, expire_on_commit=False)
    try:
        async with factory() as session:
            user = await _persist_user(session, models.User)
            database = adapter.SQLAlchemyAccessTokenDatabase(session, models.AccessToken)
            strategy = sessions.build_database_strategy(database)
            manager = _UserManager(session, models.User)
            token = await strategy.write_token(user)
            assert len(token) == 43
            assert (await strategy.read_token(token, manager)).id == USER_ID
            await session.execute(
                update(models.AccessToken)
                .where(models.AccessToken.token == token)
                .values(created_at=datetime.now(UTC) - timedelta(days=7, seconds=1))
            )
            await session.commit()
            assert await strategy.read_token(token, manager) is None
            await strategy.destroy_token(token, user)
            assert await database.get_by_token(token) is None
            assert strategy.lifetime_seconds == 7 * 24 * 60 * 60
    finally:
        await async_engine.dispose()


async def _persist_user(session: AsyncSession, user_model: type[object]) -> object:
    user = user_model(
        id=USER_ID,
        email="owner@example.test",
        hashed_password="$argon2id$v=19$test-only",
        is_active=True,
        is_superuser=False,
        is_verified=True,
    )
    session.add(user)
    await session.commit()
    return user


class _UserManager:
    def __init__(self, session: AsyncSession, user_model: type[object]) -> None:
        self._session = session
        self._user_model = user_model

    @staticmethod
    def parse_id(value: object) -> UUID:
        return UUID(str(value))

    async def get(self, user_id: UUID) -> object:
        user = await self._session.get(self._user_model, user_id)
        assert user is not None
        return user


def _has_index(inspector: object, table: str, column: str) -> bool:
    return any(column in item["column_names"] for item in inspector.get_indexes(table))


def _has_normalized_email_unique_index(engine: Engine) -> bool:
    with engine.connect() as connection:
        definition = connection.scalar(
            text("SELECT indexdef FROM pg_indexes WHERE indexname='uq_users_email_normalized'")
        )
    return isinstance(definition, str) and "UNIQUE INDEX" in definition and "lower" in definition


def _user_foreign_key(inspector: object) -> dict[str, str]:
    foreign_keys = inspector.get_foreign_keys("access_tokens")
    matching = [
        item
        for item in foreign_keys
        if item["constrained_columns"] == ["user_id"]
        and item["referred_table"] == "users"
        and item["referred_columns"] == ["id"]
    ]
    assert len(matching) == 1
    return {key.lower(): value.upper() for key, value in matching[0]["options"].items()}
