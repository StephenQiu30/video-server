from pathlib import Path

from app.core.config import Settings
from app.main import create_app


def test_auth_openapi_exposes_email_session_contract(tmp_path: Path) -> None:
    schema = create_app(
        Settings(app_env="test", frontend_dist_dir=tmp_path / "none")
    ).openapi()
    paths = schema["paths"]

    assert {
        "/api/auth/register",
        "/api/auth/login",
        "/api/auth/me",
        "/api/auth/refresh",
        "/api/auth/logout",
        "/api/users/me",
        "/api/admin/users",
        "/api/admin/users/{user_id}",
    } <= paths.keys()
    assert paths["/api/auth/register"]["post"]["operationId"] == "registerUser"
    assert paths["/api/auth/register"]["post"]["responses"]["201"]["content"][
        "application/json"
    ]["schema"] == {"$ref": "#/components/schemas/UserResponse"}
    assert paths["/api/auth/logout"]["post"]["responses"]["204"] == {
        "description": "Successful Response"
    }
    assert paths["/api/auth/refresh"]["post"]["operationId"] == ("refreshUserSession")
    request_schema = schema["components"]["schemas"]["RegisterRequest"]
    assert request_schema["additionalProperties"] is False
    assert request_schema["required"] == ["email", "password", "username"]
    assert paths["/api/admin/users"]["get"]["operationId"] == "listUsers"
    assert paths["/api/users/me"]["patch"]["operationId"] == "updateCurrentUser"
