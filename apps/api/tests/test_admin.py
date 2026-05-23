import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import User
from app.core.security import create_access_token


def test_list_users_as_admin(client: TestClient, session: Session):
    # Create admin user
    admin_user = User(
        email="admin@example.com",
        github_id="admin-gh",
        is_admin=True,
    )
    session.add(admin_user)
    session.commit()
    session.refresh(admin_user)

    # Create token directly
    token = create_access_token(admin_user.id)

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
        github_id="normal-gh",
        is_admin=False,
    )
    session.add(normal_user)
    session.commit()
    session.refresh(normal_user)

    # Create token directly
    token = create_access_token(normal_user.id)

    # Try list users
    response = client.get(
        "/api/admin/users",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403
    assert response.json()["success"] is False
    assert response.json()["error"]["code"] == "forbidden"


def test_update_user_quota(client: TestClient, session: Session):
    # Admin
    admin_user = User(email="admin2@example.com", github_id="admin2-gh", is_admin=True)
    session.add(admin_user)
    
    # Target user
    target_user = User(email="target@example.com", github_id="target-gh", daily_task_quota=10)
    session.add(target_user)
    session.commit()
    session.refresh(admin_user)
    session.refresh(target_user)
    target_id = target_user.id

    token = create_access_token(admin_user.id)

    response = client.patch(
        f"/api/admin/users/{target_id}",
        json={"daily_task_quota": 99},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["daily_task_quota"] == 99
