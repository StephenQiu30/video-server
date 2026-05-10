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
