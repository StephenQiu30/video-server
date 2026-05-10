import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import User
from app.core.security import hash_password


def test_list_users_as_admin(client: TestClient, session: Session):
    # Create admin user
    admin_user = User(
        email="admin@example.com",
        password_hash=hash_password("adminpw"),
        is_admin=True,
    )
    session.add(admin_user)
    session.commit()

    # Login to get token
    login_res = client.post(
        "/api/auth/login",
        data={"username": "admin@example.com", "password": "adminpw"},
    )
    token = login_res.json()["access_token"]

    # List users
    response = client.get(
        "/api/admin/users",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert len(response.json()) >= 1


def test_list_users_as_non_admin_fails(client: TestClient, session: Session):
    # Create normal user
    normal_user = User(
        email="normal@example.com",
        password_hash=hash_password("pw"),
        is_admin=False,
    )
    session.add(normal_user)
    session.commit()

    # Login to get token
    login_res = client.post(
        "/api/auth/login",
        data={"username": "normal@example.com", "password": "pw"},
    )
    token = login_res.json()["access_token"]

    # Try list users
    response = client.get(
        "/api/admin/users",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403
    assert "enough privileges" in response.json()["detail"]


def test_update_user_quota(client: TestClient, session: Session):
    # Admin
    admin_user = User(email="admin2@example.com", password_hash=hash_password("pw"), is_admin=True)
    session.add(admin_user)
    
    # Target user
    target_user = User(email="target@example.com", password_hash=hash_password("pw"), daily_task_quota=10)
    session.add(target_user)
    session.commit()
    session.refresh(target_user)
    target_id = target_user.id

    login_res = client.post("/api/auth/login", data={"username": "admin2@example.com", "password": "pw"})
    token = login_res.json()["access_token"]

    response = client.patch(
        f"/api/admin/users/{target_id}",
        json={"daily_task_quota": 99},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["daily_task_quota"] == 99
