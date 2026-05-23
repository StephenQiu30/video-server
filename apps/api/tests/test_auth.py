import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import User
from app.core.security import create_access_token


def test_get_me(client: TestClient, session: Session):
    email = "me@example.com"
    user = User(
        email=email,
        display_name="Me User",
        github_id="12345",
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    # Create token directly to bypass removed login endpoint
    token = create_access_token(user.id)

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["email"] == email
    assert response.json()["display_name"] == "Me User"


def test_register_creates_user_and_returns_token(client: TestClient):
    response = client.post(
        "/api/auth/register",
        json={"email": "register@example.com", "password": "password123", "display_name": "Register"},
    )

    assert response.status_code == 201
    assert response.json()["token_type"] == "bearer"
    assert response.json()["access_token"]


def test_login_locks_after_repeated_failures(monkeypatch, client: TestClient, session: Session):
    from app.routers import auth
    from app.services.auth_lock import InMemoryAuthLock

    lock = InMemoryAuthLock(max_failures=2, lock_seconds=900)
    monkeypatch.setattr(auth, "get_auth_lock", lambda: lock)
    user = User(
        email="locked@example.com",
        password_hash="$2b$12$Qd4Uezi1rZrhTUiTjnw3KuwIqgmfs.satmmYzDeAU3Z5Sy0rYowRa",
    )
    session.add(user)
    session.commit()

    for _ in range(2):
        response = client.post(
            "/api/auth/login",
            json={"email": "locked@example.com", "password": "wrong-password"},
        )
        assert response.status_code == 401

    locked = client.post(
        "/api/auth/login",
        json={"email": "locked@example.com", "password": "wrong-password"},
    )

    assert locked.status_code == 429
    assert locked.json()["error"]["code"] == "auth_locked"
    assert "存在" not in locked.json()["error"]["message"]


def test_successful_login_clears_email_lock(monkeypatch, client: TestClient, session: Session):
    from app.core.security import hash_password
    from app.routers import auth
    from app.services.auth_lock import InMemoryAuthLock

    lock = InMemoryAuthLock(max_failures=2, lock_seconds=900)
    monkeypatch.setattr(auth, "get_auth_lock", lambda: lock)
    user = User(email="clear@example.com", password_hash=hash_password("password123"))
    session.add(user)
    session.commit()

    lock.record_login_failure("clear@example.com", "testclient")
    assert lock.is_login_locked("clear@example.com", "testclient") is False

    response = client.post(
        "/api/auth/login",
        json={"email": "clear@example.com", "password": "password123"},
    )

    assert response.status_code == 200
