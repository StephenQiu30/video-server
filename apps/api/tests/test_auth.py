import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import User
from app.core.security import hash_password


def test_register_success(client: TestClient):
    response = client.post(
        "/api/auth/register",
        json={"email": "test@example.com", "password": "password123", "display_name": "Test User"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["display_name"] == "Test User"
    assert "id" in data


def test_register_duplicate_email(client: TestClient, session: Session):
    user = User(email="duplicate@example.com", password_hash=hash_password("pw"))
    session.add(user)
    session.commit()

    response = client.post(
        "/api/auth/register",
        json={"email": "duplicate@example.com", "password": "password123"},
    )
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"]


def test_login_success(client: TestClient, session: Session):
    email = "login@example.com"
    password = "correct_password"
    user = User(email=email, password_hash=hash_password(password))
    session.add(user)
    session.commit()

    response = client.post(
        "/api/auth/login",
        data={"username": email, "password": password},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_invalid_credentials(client: TestClient, session: Session):
    email = "wrong@example.com"
    user = User(email=email, password_hash=hash_password("correct"))
    session.add(user)
    session.commit()

    response = client.post(
        "/api/auth/login",
        data={"username": email, "password": "wrong_password"},
    )
    assert response.status_code == 401


def test_get_me(client: TestClient, session: Session):
    email = "me@example.com"
    password = "pw"
    user = User(email=email, password_hash=hash_password(password))
    session.add(user)
    session.commit()

    # Login to get token
    login_res = client.post(
        "/api/auth/login",
        data={"username": email, "password": password},
    )
    token = login_res.json()["access_token"]

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["email"] == email


def test_register_disabled(client: TestClient, monkeypatch):
    from app.core.config import Settings
    def mock_get_settings():
        return Settings(registration_enabled=False)
    
    monkeypatch.setattr("app.routers.auth.get_settings", mock_get_settings)

    response = client.post(
        "/api/auth/register",
        json={"email": "disabled@example.com", "password": "password123"},
    )
    assert response.status_code == 403
    assert "disabled" in response.json()["detail"]


def test_register_invalid_invite_code(client: TestClient, monkeypatch):
    from app.core.config import Settings
    def mock_get_settings():
        return Settings(registration_enabled=True, registration_invite_code="SECRET")
    
    monkeypatch.setattr("app.routers.auth.get_settings", mock_get_settings)

    response = client.post(
        "/api/auth/register",
        json={"email": "invite@example.com", "password": "password123", "invite_code": "WRONG"},
    )
    assert response.status_code == 403
    assert "Invalid invite code" in response.json()["detail"]
