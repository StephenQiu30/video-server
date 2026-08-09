from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from app.application.auth import AuthService
from app.core.config import Settings
from app.infrastructure.auth_repository import SqlAlchemyAuthRepository
from app.infrastructure.database import Base, create_engine, create_session_factory
from app.infrastructure.jwt_tokens import JwtTokenService
from app.infrastructure.passwords import Argon2PasswordHasher
from app.main import create_app
from httpx import ASGITransport, AsyncClient


@asynccontextmanager
async def auth_client(tmp_path: Path) -> AsyncIterator[AsyncClient]:
    engine = create_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    service = AuthService(
        repository=SqlAlchemyAuthRepository(create_session_factory(engine)),
        passwords=Argon2PasswordHasher(),
        tokens=JwtTokenService(
            secret=b"s" * 48,
            issuer="video-server-test",
            audience="video-web-test",
            access_ttl=timedelta(minutes=15),
            refresh_ttl=timedelta(days=30),
        ),
        now=lambda: datetime.now(UTC),
        new_id=uuid4,
    )
    app = create_app(
        Settings(
            app_env="test",
            auth_access_cookie_name="test_access",
            auth_refresh_cookie_name="test_refresh",
            auth_jwt_issuer="video-server-test",
            auth_jwt_audience="video-web-test",
            frontend_dist_dir=tmp_path / "missing",
        )
    )
    app.state.auth_service = service
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        yield client
    await engine.dispose()


async def test_register_creates_http_only_session_and_logout_revokes_it(
    tmp_path: Path,
) -> None:
    async with auth_client(tmp_path) as client:
        registered = await client.post(
            "/api/auth/register",
            json={"email": " User@Example.com ", "password": "strong-pass-123"},
        )
        current = await client.get("/api/auth/me")
        client.cookies.delete("test_access")
        silently_restored = await client.get("/api/auth/me")
        logged_out = await client.post("/api/auth/logout")
        after_logout = await client.get("/api/auth/me")

    assert registered.status_code == 201
    assert registered.headers["location"] == "/api/auth/me"
    assert registered.json()["email"] == "user@example.com"
    cookie = registered.headers["set-cookie"].lower()
    assert "httponly" in cookie
    assert "samesite=lax" in cookie
    assert "test_access=" in cookie
    assert "test_refresh=" in cookie
    assert current.status_code == 200
    assert current.json() == registered.json()
    assert silently_restored.status_code == 200
    assert silently_restored.json() == registered.json()
    assert "test_access=" in silently_restored.headers["set-cookie"].lower()
    assert logged_out.status_code == 204
    assert logged_out.headers["set-cookie"].lower().count("max-age=0") == 2
    assert after_logout.status_code == 401
    assert after_logout.json()["code"] == "unauthenticated"


async def test_login_uses_generic_errors_and_duplicate_email_is_rejected(
    tmp_path: Path,
) -> None:
    credentials = {"email": "user@example.com", "password": "strong-pass-123"}
    async with auth_client(tmp_path) as client:
        assert (await client.post("/api/auth/register", json=credentials)).is_success
        duplicate = await client.post("/api/auth/register", json=credentials)
        wrong = await client.post(
            "/api/auth/login",
            json={"email": credentials["email"], "password": "wrong-password"},
        )
        logged_in = await client.post("/api/auth/login", json=credentials)

    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "email_already_registered"
    assert wrong.status_code == 401
    assert wrong.json() == {
        "type": "urn:video-server:error:invalid_credentials",
        "title": "Invalid credentials",
        "status": 401,
        "detail": "The email or password is incorrect.",
        "code": "invalid_credentials",
        "instance": "/api/auth/login",
    }
    assert logged_in.status_code == 200


async def test_auth_contract_validates_input_and_protects_business_routes(
    tmp_path: Path,
) -> None:
    async with auth_client(tmp_path) as client:
        invalid_email = await client.post(
            "/api/auth/register",
            json={"email": "invalid", "password": "strong-pass-123"},
        )
        short_password = await client.post(
            "/api/auth/register",
            json={"email": "user@example.com", "password": "short"},
        )
        history = await client.get("/api/downloads/history")

    assert invalid_email.status_code == short_password.status_code == 422
    assert history.status_code == 401
    assert history.json()["code"] == "unauthenticated"
