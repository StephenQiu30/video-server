from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from app.core.config import Settings
from app.core.db import create_session_factory
from app.integrations.jwt_tokens import JwtTokenService
from app.integrations.passwords import Argon2PasswordHasher
from app.main import create_app
from app.repositories.auth.auth_repository import SqlAlchemyAuthRepository
from app.repositories.auth.email_verification_repository import (
    SqlAlchemyVerificationStore,
)
from app.repositories.auth.user_repository import SqlAlchemyUserRepository
from app.repositories.auth.web_sessions import WebSessionRepository
from app.services.auth.email_verification import EmailVerification
from app.services.auth.service import AuthService
from app.services.auth.user_service import UserService
from app.services.auth.web_sessions import WebSessionService
from httpx import ASGITransport, AsyncClient, Response
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncEngine


class CapturingMailer:
    def __init__(self) -> None:
        self.codes: dict[str, str] = {}

    async def send_code(self, email: str, code: str) -> None:
        self.codes[email] = code


class AuthTestClient(AsyncClient):
    mailer: CapturingMailer

    async def register(
        self, url: str, *, json: dict[str, str], headers: dict[str, str] | None = None
    ) -> Response:
        await self.post(
            url.removesuffix("register") + "registration-code",
            json={"email": json["email"]},
        )
        code = self.mailer.codes.get(json["email"].strip().casefold(), "000000")
        await self.post(
            url.removesuffix("register") + "registration-code/verify",
            json={"email": json["email"], "verification_code": code},
        )
        return await self.post(
            url, json={**json, "verification_code": code}, headers=headers
        )


@asynccontextmanager
async def auth_client(
    tmp_path: Path,
    engine: AsyncEngine,
    bootstrap_admin_email: str | None = None,
    bootstrap_admin_secret: str | None = None,
) -> AsyncIterator[AuthTestClient]:
    sessions = create_session_factory(engine)
    mailer = CapturingMailer()
    service = AuthService(
        verification=EmailVerification(
            SqlAlchemyVerificationStore(sessions),
            mailer,
            b"s" * 48,
            lambda: datetime.now(UTC),
        ),
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
        bootstrap_admin_secret=bootstrap_admin_secret,
    )
    user_service = UserService(
        repository=SqlAlchemyUserRepository(sessions),
        now=lambda: datetime.now(UTC),
    )
    app = create_app(
        Settings(
            app_env="test",
            auth_web_cookie_name="test_web",
            auth_jwt_issuer="video-server-test",
            auth_jwt_audience="video-web-test",
        )
    )
    app.state.services.auth_service = service
    app.state.services.user_service = user_service
    app.state.services.web_session_service = WebSessionService(
        WebSessionRepository(sessions),
        now=lambda: datetime.now(UTC),
        idle_ttl=timedelta(days=7),
        absolute_ttl=timedelta(days=30),
    )
    async with AuthTestClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        headers={"Origin": "http://testserver"},
    ) as client:
        client.mailer = mailer
        yield client


async def test_register_creates_http_only_session_and_logout_revokes_it(
    tmp_path: Path,
    postgres_engine: AsyncEngine,
) -> None:
    async with auth_client(tmp_path, postgres_engine) as client:
        registered = await client.register(
            "/api/auth/register",
            json={
                "username": "VideoUser",
                "email": " User@Example.com ",
                "password": "strong-pass-123",
            },
        )
        current = await client.get("/api/auth/me")
        token = client.cookies.get("test_web")
        client.cookies.clear()
        without_access = await client.get("/api/auth/me")
        client.cookies.set("test_web", token)
        restored = await client.get("/api/auth/me")
        logged_out = await client.post("/api/auth/logout")
        after_logout = await client.get("/api/auth/me")

    assert registered.status_code == 201
    assert registered.headers["location"] == "/api/auth/me"
    assert registered.json()["data"]["email"] == "user@example.com"
    assert registered.json()["data"]["username"] == "VideoUser"
    assert registered.json()["data"]["role"] == "user"
    cookie = registered.headers["set-cookie"].lower()
    assert "httponly" in cookie
    assert "samesite=lax" in cookie
    assert "test_web=" in cookie
    assert len(registered.headers.get_list("set-cookie")) == 1
    assert current.status_code == 200
    assert current.json() == registered.json()
    assert without_access.status_code == 401
    assert "set-cookie" not in without_access.headers
    assert "set-cookie" not in restored.headers
    assert restored.status_code == 200
    assert restored.json() == registered.json()
    assert logged_out.status_code == 204
    assert logged_out.headers["set-cookie"].lower().count("max-age=0") == 1
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
        assert (
            await client.register("/api/auth/register", json=credentials)
        ).is_success
        duplicate = await client.register(
            "/api/auth/register",
            json={**credentials, "username": "another_user"},
        )
        duplicate_username = await client.register(
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
        "code": "invalid_credentials",
        "message": "The email or password is incorrect.",
        "data": None,
    }
    assert logged_in.status_code == 200


async def test_auth_contract_validates_input_and_protects_business_routes(
    tmp_path: Path,
    postgres_engine: AsyncEngine,
) -> None:
    async with auth_client(tmp_path, postgres_engine) as client:
        invalid_email = await client.register(
            "/api/auth/register",
            json={
                "username": "valid_user",
                "email": "invalid",
                "password": "strong-pass-123",
            },
        )
        short_password = await client.register(
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
    bootstrap_secret = "test-admin-bootstrap-secret-32-bytes"
    async with auth_client(
        tmp_path,
        postgres_engine,
        admin_credentials["email"],
        bootstrap_secret,
    ) as client:
        admin = await client.register(
            "/api/auth/register",
            json=admin_credentials,
            headers={"X-Admin-Bootstrap-Secret": bootstrap_secret},
        )
        await client.post("/api/auth/logout")
        user = await client.register("/api/auth/register", json=user_credentials)
        updated_profile = await client.patch(
            "/api/users/me", json={"username": "renamed_user"}
        )
        user_session = client.cookies.get("test_web")
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
        user_id = user.json()["data"]["id"]
        promoted = await client.patch(
            f"/api/admin/users/{user_id}",
            json={
                "role": "admin",
                "quota": {
                    "exempt": False,
                    "max_active_per_owner": 9,
                    "daily_tasks": 120,
                    "daily_bytes": 512 * 1024**2,
                    "storage_bytes": 2 * 1024**3,
                    "daily_analysis_attempts": 80,
                },
            },
        )
        disabled = await client.patch(
            f"/api/admin/users/{user_id}", json={"is_active": False}
        )
        self_demote = await client.patch(
            f"/api/admin/users/{admin.json()['data']['id']}", json={"role": "user"}
        )
        self_delete = await client.delete(
            f"/api/admin/users/{admin.json()['data']['id']}"
        )
        deleted = await client.delete(f"/api/admin/users/{user_id}")
        after_delete = await client.get(
            "/api/admin/users", params={"search": "renamed"}
        )
        missing_delete = await client.delete(f"/api/admin/users/{user_id}")
        client.cookies.clear()
        client.cookies.set("test_web", user_session)
        revoked_session = await client.get("/api/auth/me")

    assert admin.json()["data"]["role"] == "admin"
    assert user.json()["data"]["role"] == "user"
    assert updated_profile.status_code == 200
    assert updated_profile.json()["data"]["username"] == "renamed_user"
    assert forbidden.status_code == 403
    assert forbidden.json()["code"] == "forbidden"
    assert users.status_code == 200
    assert users.json()["data"]["total"] == 1
    assert users.json()["data"]["items"][0]["username"] == "renamed_user"
    assert promoted.json()["data"]["role"] == "admin"
    assert promoted.json()["data"]["quota"] == {
        "exempt": False,
        "max_active_per_owner": 9,
        "daily_tasks": 120,
        "daily_bytes": 512 * 1024**2,
        "storage_bytes": 2 * 1024**3,
        "daily_analysis_attempts": 80,
    }
    assert disabled.json()["data"]["is_active"] is False
    assert self_demote.status_code == 409
    assert self_demote.json()["code"] == "self_admin_change"
    assert self_delete.status_code == 409
    assert self_delete.json()["code"] == "self_admin_change"
    assert deleted.status_code == 204
    assert after_delete.status_code == 200
    assert after_delete.json()["data"]["total"] == 0
    assert missing_delete.status_code == 404
    assert missing_delete.json()["code"] == "user_not_found"
    assert revoked_session.status_code == 401
    assert "set-cookie" not in revoked_session.headers


async def test_configured_bootstrap_email_requires_the_bootstrap_secret(
    tmp_path: Path,
    postgres_engine: AsyncEngine,
) -> None:
    bootstrap_secret = "test-admin-bootstrap-secret-32-bytes"
    async with auth_client(
        tmp_path, postgres_engine, "admin@example.com", bootstrap_secret
    ) as client:
        member = await client.register(
            "/api/auth/register",
            json={
                "username": "first_member",
                "email": "member@example.com",
                "password": "strong-pass-123",
            },
        )
        await client.post("/api/auth/logout")
        missing_secret = await client.register(
            "/api/auth/register",
            json={
                "username": "configured_admin",
                "email": "Admin@Example.com",
                "password": "strong-pass-456",
            },
        )
        wrong_secret = await client.register(
            "/api/auth/register",
            json={
                "username": "configured_admin",
                "email": "Admin@Example.com",
                "password": "strong-pass-456",
            },
            headers={"X-Admin-Bootstrap-Secret": "incorrect-secret"},
        )
        admin = await client.register(
            "/api/auth/register",
            json={
                "username": "configured_admin",
                "email": "Admin@Example.com",
                "password": "strong-pass-456",
            },
            headers={"X-Admin-Bootstrap-Secret": bootstrap_secret},
        )

    assert member.json()["data"]["role"] == "user"
    assert missing_secret.status_code == 403
    assert missing_secret.json()["code"] == "admin_bootstrap_required"
    assert wrong_secret.status_code == 403
    assert admin.json()["data"]["role"] == "admin"


async def test_native_session_rotates_refresh_and_logout_revokes_it(
    tmp_path: Path,
    postgres_engine: AsyncEngine,
) -> None:
    credentials = {
        "username": "native_member",
        "email": "native@example.com",
        "password": "strong-pass-123",
    }
    async with auth_client(tmp_path, postgres_engine) as client:
        registered = await client.register(
            "/api/app/v1/auth/register", json=credentials
        )
        first_session = registered.json()
        current = await client.get(
            "/api/app/v1/auth/me",
            headers={"Authorization": f"Bearer {first_session['access_token']}"},
        )
        refreshed = await client.post(
            "/api/app/v1/auth/refresh",
            json={"refresh_token": first_session["refresh_token"]},
        )
        second_session = refreshed.json()
        replay = await client.post(
            "/api/app/v1/auth/refresh",
            json={"refresh_token": first_session["refresh_token"]},
        )
        logged_out = await client.post(
            "/api/app/v1/auth/logout",
            json={"refresh_token": second_session["refresh_token"]},
        )
        after_logout = await client.post(
            "/api/app/v1/auth/refresh",
            json={"refresh_token": second_session["refresh_token"]},
        )

    assert registered.status_code == 201
    assert "set-cookie" not in registered.headers
    assert registered.headers["location"] == "/api/app/v1/auth/me"
    assert first_session["token_type"] == "Bearer"
    assert first_session["user"]["email"] == credentials["email"]
    assert first_session["access_expires_at"]
    assert first_session["refresh_expires_at"]
    assert current.status_code == 200
    assert current.json()["email"] == credentials["email"]
    assert refreshed.status_code == 200
    assert second_session["access_token"] != first_session["access_token"]
    assert second_session["refresh_token"] != first_session["refresh_token"]
    assert replay.status_code == 401
    assert logged_out.status_code == 204
    assert after_logout.status_code == 401


async def test_invalid_bearer_does_not_fall_back_to_browser_cookie(
    tmp_path: Path,
    postgres_engine: AsyncEngine,
) -> None:
    async with auth_client(tmp_path, postgres_engine) as client:
        registered = await client.register(
            "/api/auth/register",
            json={
                "username": "browser_member",
                "email": "browser@example.com",
                "password": "strong-pass-123",
            },
        )
        current = await client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer invalid-access-token"},
        )

    assert registered.status_code == 201
    assert current.status_code == 401


async def test_web_and_native_credentials_are_not_interchangeable(
    tmp_path, postgres_engine
):
    async with auth_client(tmp_path, postgres_engine) as client:
        registered = await client.register(
            "/api/auth/register",
            json={
                "username": "isolated_user",
                "email": "isolated@example.com",
                "password": "strong-pass-123",
            },
        )
        assert registered.status_code == 201
        assert (await client.get("/api/app/v1/auth/me")).status_code == 401
        native = await client.post(
            "/api/app/v1/auth/login",
            json={"email": "isolated@example.com", "password": "strong-pass-123"},
        )
        headers = {"Authorization": f"Bearer {native.json()['access_token']}"}
        assert (await client.get("/api/auth/me", headers=headers)).status_code == 401
        assert (
            await client.get("/api/app/v1/auth/me", headers=headers)
        ).status_code == 200
        assert (
            await client.get(
                "/api/downloads/history", headers={"Authorization": "Basic invalid"}
            )
        ).status_code == 401


async def test_web_session_store_outage_preserves_cookie_and_recovers(
    tmp_path, postgres_engine
):
    from unittest.mock import patch

    from app.services.auth.errors import SessionStoreUnavailable

    async with auth_client(tmp_path, postgres_engine) as client:
        await client.register(
            "/api/auth/register",
            json={
                "username": "outage_user",
                "email": "outage@example.com",
                "password": "strong-pass-123",
            },
        )
        token = client.cookies.get("test_web")
        with patch.object(
            WebSessionRepository, "current_user", side_effect=SessionStoreUnavailable
        ):
            failed = await client.get("/api/auth/me")
        assert failed.status_code == 503
        assert failed.json()["code"] == "service_unavailable"
        assert "set-cookie" not in failed.headers
        with patch.object(
            WebSessionRepository, "revoke", side_effect=SessionStoreUnavailable
        ):
            failed_logout = await client.post("/api/auth/logout")
        assert failed_logout.status_code == 503
        assert "set-cookie" not in failed_logout.headers
        assert client.cookies.get("test_web") == token
        restored = await client.get("/api/auth/me")
        assert restored.status_code == 200
        assert restored.headers["cache-control"] == "no-store"
        assert "set-cookie" not in restored.headers
        await client.post("/api/auth/logout")
        client.cookies.set("test_web", token)
        assert (await client.get("/api/auth/me")).status_code == 401


async def test_avatar_upload_replaces_and_removes_private_image(
    tmp_path: Path, postgres_engine: AsyncEngine
) -> None:
    image = BytesIO()
    Image.new("RGB", (640, 320), "#2468ac").save(image, format="PNG")
    async with auth_client(tmp_path, postgres_engine) as client:
        await client.register(
            "/api/auth/register",
            json={
                "username": "avatar_user",
                "email": "avatar@example.com",
                "password": "strong-pass-123",
            },
        )
        missing = await client.get("/api/users/me/avatar")
        uploaded = await client.put(
            "/api/users/me/avatar",
            content=image.getvalue(),
            headers={"Content-Type": "application/octet-stream"},
        )
        avatar = await client.get("/api/users/me/avatar")
        current = await client.get("/api/auth/me")
        renamed = await client.patch(
            "/api/users/me", json={"username": "avatar_renamed"}
        )
        version = uploaded.json()["data"]["avatar_version"]
        await client.post("/api/auth/logout")
        anonymous = await client.get("/api/users/me/avatar")
        await client.register(
            "/api/auth/register",
            json={
                "username": "second_user",
                "email": "second@example.com",
                "password": "strong-pass-456",
            },
        )
        other_user = await client.get("/api/users/me/avatar")
        await client.post("/api/auth/logout")
        await client.post(
            "/api/auth/login",
            json={"email": "avatar@example.com", "password": "strong-pass-123"},
        )
        removed = await client.delete("/api/users/me/avatar")
        after_remove = await client.get("/api/users/me/avatar")

    assert missing.status_code == 404
    assert uploaded.status_code == 200
    assert version
    assert avatar.status_code == 200
    assert avatar.headers["content-type"] == "image/webp"
    assert avatar.headers["cache-control"] == "private, no-store"
    with Image.open(BytesIO(avatar.content)) as normalized:
        assert normalized.format == "WEBP"
        assert normalized.size == (256, 256)
        assert "exif" not in normalized.info
    assert current.json()["data"]["avatar_version"] == version
    assert renamed.json()["data"]["avatar_version"] == version
    assert anonymous.status_code == 401
    assert other_user.status_code == 404
    assert removed.json()["data"]["avatar_version"] is None
    assert after_remove.status_code == 404


async def test_avatar_upload_rejects_invalid_and_oversized_images(
    tmp_path: Path, postgres_engine: AsyncEngine
) -> None:
    async with auth_client(tmp_path, postgres_engine) as client:
        await client.register(
            "/api/auth/register",
            json={
                "username": "avatar_validation",
                "email": "avatar-validation@example.com",
                "password": "strong-pass-123",
            },
        )
        invalid = await client.put(
            "/api/users/me/avatar",
            content=b"<svg><script>alert(1)</script></svg>",
            headers={"Content-Type": "application/octet-stream"},
        )
        oversized = await client.put(
            "/api/users/me/avatar",
            content=b"x" * (4 * 1024 * 1024 + 1),
            headers={"Content-Type": "application/octet-stream"},
        )
        current = await client.get("/api/auth/me")

    assert invalid.status_code == 422
    assert invalid.json()["code"] == "invalid_request"
    assert oversized.status_code == 413
    assert current.json()["data"]["avatar_version"] is None
