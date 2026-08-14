from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from app.application.auth import AuthService, UserService
from app.core.config import Settings
from app.infrastructure.auth_repository import SqlAlchemyAuthRepository
from app.infrastructure.database import create_session_factory
from app.infrastructure.jwt_tokens import JwtTokenService
from app.infrastructure.passwords import Argon2PasswordHasher
from app.infrastructure.user_repository import SqlAlchemyUserRepository
from app.main import create_app
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine


@asynccontextmanager
async def auth_client(
    tmp_path: Path,
    engine: AsyncEngine,
    bootstrap_admin_email: str | None = None,
) -> AsyncIterator[AsyncClient]:
    sessions = create_session_factory(engine)
    service = AuthService(
        repository=SqlAlchemyAuthRepository(sessions),
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
        bootstrap_admin_email=bootstrap_admin_email,
    )
    user_service = UserService(
        repository=SqlAlchemyUserRepository(sessions),
        now=lambda: datetime.now(UTC),
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
    app.state.user_service = user_service
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        yield client


async def test_register_creates_http_only_session_and_logout_revokes_it(
    tmp_path: Path,
    postgres_engine: AsyncEngine,
) -> None:
    async with auth_client(tmp_path, postgres_engine) as client:
        registered = await client.post(
            "/api/auth/register",
            json={
                "username": "VideoUser",
                "email": " User@Example.com ",
                "password": "strong-pass-123",
            },
        )
        current = await client.get("/api/auth/me")
        client.cookies.delete("test_access")
        silently_restored = await client.get("/api/auth/me")
        logged_out = await client.post("/api/auth/logout")
        after_logout = await client.get("/api/auth/me")

    assert registered.status_code == 201
    assert registered.headers["location"] == "/api/auth/me"
    assert registered.json()["email"] == "user@example.com"
    assert registered.json()["username"] == "VideoUser"
    assert registered.json()["role"] == "admin"
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
    postgres_engine: AsyncEngine,
) -> None:
    credentials = {
        "username": "video_user",
        "email": "user@example.com",
        "password": "strong-pass-123",
    }
    async with auth_client(tmp_path, postgres_engine) as client:
        assert (await client.post("/api/auth/register", json=credentials)).is_success
        duplicate = await client.post(
            "/api/auth/register",
            json={**credentials, "username": "another_user"},
        )
        duplicate_username = await client.post(
            "/api/auth/register",
            json={**credentials, "email": "another@example.com"},
        )
        wrong = await client.post(
            "/api/auth/login",
            json={"email": credentials["email"], "password": "wrong-password"},
        )
        logged_in = await client.post(
            "/api/auth/login",
            json={"email": credentials["email"], "password": credentials["password"]},
        )

    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "email_already_registered"
    assert duplicate_username.status_code == 409
    assert duplicate_username.json()["code"] == "username_already_registered"
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
    postgres_engine: AsyncEngine,
) -> None:
    async with auth_client(tmp_path, postgres_engine) as client:
        invalid_email = await client.post(
            "/api/auth/register",
            json={
                "username": "valid_user",
                "email": "invalid",
                "password": "strong-pass-123",
            },
        )
        short_password = await client.post(
            "/api/auth/register",
            json={
                "username": "valid_user",
                "email": "user@example.com",
                "password": "short",
            },
        )
        history = await client.get("/api/downloads/history")

    assert invalid_email.status_code == short_password.status_code == 422
    assert history.status_code == 401
    assert history.json()["code"] == "unauthenticated"


async def test_profile_and_admin_user_management_are_role_protected(
    tmp_path: Path,
    postgres_engine: AsyncEngine,
) -> None:
    admin_credentials = {
        "username": "admin_user",
        "email": "admin@example.com",
        "password": "strong-pass-123",
    }
    user_credentials = {
        "username": "normal_user",
        "email": "user@example.com",
        "password": "strong-pass-456",
    }
    async with auth_client(tmp_path, postgres_engine) as client:
        admin = await client.post("/api/auth/register", json=admin_credentials)
        await client.post("/api/auth/logout")
        user = await client.post("/api/auth/register", json=user_credentials)
        updated_profile = await client.patch(
            "/api/users/me", json={"username": "renamed_user"}
        )
        user_refresh = client.cookies.get("test_refresh")
        forbidden = await client.get("/api/admin/users")
        await client.post("/api/auth/logout")
        await client.post(
            "/api/auth/login",
            json={
                "email": admin_credentials["email"],
                "password": admin_credentials["password"],
            },
        )
        users = await client.get(
            "/api/admin/users", params={"search": "renamed", "role": "user"}
        )
        user_id = user.json()["id"]
        promoted = await client.patch(
            f"/api/admin/users/{user_id}", json={"role": "admin"}
        )
        disabled = await client.patch(
            f"/api/admin/users/{user_id}", json={"is_active": False}
        )
        self_demote = await client.patch(
            f"/api/admin/users/{admin.json()['id']}", json={"role": "user"}
        )
        client.cookies.clear()
        client.cookies.set("test_refresh", user_refresh)
        revoked_session = await client.get("/api/auth/me")

    assert admin.json()["role"] == "admin"
    assert user.json()["role"] == "user"
    assert updated_profile.status_code == 200
    assert updated_profile.json()["username"] == "renamed_user"
    assert forbidden.status_code == 403
    assert forbidden.json()["code"] == "forbidden"
    assert users.status_code == 200
    assert users.json()["total"] == 1
    assert users.json()["items"][0]["username"] == "renamed_user"
    assert promoted.json()["role"] == "admin"
    assert disabled.json()["is_active"] is False
    assert self_demote.status_code == 409
    assert self_demote.json()["code"] == "self_admin_change"
    assert revoked_session.status_code == 401


async def test_configured_bootstrap_email_receives_admin_role(
    tmp_path: Path,
    postgres_engine: AsyncEngine,
) -> None:
    async with auth_client(tmp_path, postgres_engine, "admin@example.com") as client:
        member = await client.post(
            "/api/auth/register",
            json={
                "username": "first_member",
                "email": "member@example.com",
                "password": "strong-pass-123",
            },
        )
        await client.post("/api/auth/logout")
        admin = await client.post(
            "/api/auth/register",
            json={
                "username": "configured_admin",
                "email": "Admin@Example.com",
                "password": "strong-pass-456",
            },
        )

    assert member.json()["role"] == "user"
    assert admin.json()["role"] == "admin"
