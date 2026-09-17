from __future__ import annotations

import pytest
from app.models.ai_provider import AiProviderProfileRow
from sqlalchemy import bindparam, insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine


@pytest.mark.asyncio
async def test_api_engine_constraints_allow_valid_routes_and_reject_host_login(
    postgres_engine: AsyncEngine,
) -> None:
    statement = insert(AiProviderProfileRow).values(
        key=bindparam("key"),
        display_name="API",
        engine=bindparam("engine"),
        auth_mode=bindparam("auth"),
        base_url=bindparam("url"),
        model="vendor/model",
        credential_ciphertext=bindparam("secret"),
        credential_key_id=bindparam("key_id"),
    )
    async with postgres_engine.begin() as connection:
        for engine in ("openrouter", "openai"):
            await connection.execute(
                statement,
                dict(
                    key=engine,
                    engine=engine,
                    auth="api_key",
                    url="https://openrouter.ai/api/v1",
                    secret=b"controlled-ciphertext",
                    key_id="test",
                ),
            )
    for engine in ("openrouter", "openai"):
        with pytest.raises(IntegrityError):
            async with postgres_engine.begin() as connection:
                await connection.execute(
                    statement,
                    dict(
                        key="invalid-" + engine,
                        engine=engine,
                        auth="host_login",
                        url=None,
                        secret=None,
                        key_id=None,
                    ),
                )
    with pytest.raises(IntegrityError):
        async with postgres_engine.begin() as connection:
            await connection.execute(
                statement,
                dict(
                    key="wrong-endpoint",
                    engine="openrouter",
                    auth="api_key",
                    url="https://other.example/v1",
                    secret=b"controlled-ciphertext",
                    key_id="test",
                ),
            )
