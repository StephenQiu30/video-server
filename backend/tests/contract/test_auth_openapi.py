from pathlib import Path

from app.api.routes.native_openapi import build_native_openapi
from app.core.config import Settings
from app.main import create_app


def test_auth_openapi_exposes_email_session_contract(tmp_path: Path) -> None:
    schema = create_app(Settings(app_env="test")).openapi()
    paths = schema["paths"]

    assert {
        "/api/auth/register",
        "/api/auth/registration-code/verify",
        "/api/auth/login",
        "/api/auth/me",
        "/api/auth/logout",
        "/api/app/v1/auth/register",
        "/api/app/v1/auth/registration-code",
        "/api/app/v1/auth/registration-code/verify",
        "/api/app/v1/auth/login",
        "/api/app/v1/auth/me",
        "/api/app/v1/auth/refresh",
        "/api/app/v1/auth/logout",
        "/api/users/me",
        "/api/users/me/avatar",
        "/api/admin/users",
        "/api/admin/users/{user_id}",
        "/api/admin/providers",
        "/api/admin/providers/{provider_key}",
    } <= paths.keys()
    assert paths["/api/auth/register"]["post"]["operationId"] == "registerUser"
    assert paths["/api/auth/registration-code/verify"]["post"]["operationId"] == (
        "verifyRegistrationCode"
    )
    assert paths["/api/auth/register"]["post"]["responses"]["201"]["content"][
        "application/json"
    ]["schema"] == {"$ref": "#/components/schemas/ApiResponse_UserResponse_"}
    assert paths["/api/auth/logout"]["post"]["responses"]["204"] == {
        "description": "Successful Response"
    }
    assert "/api/auth/refresh" not in paths
    request_schema = schema["components"]["schemas"]["RegisterRequest"]
    assert request_schema["additionalProperties"] is False
    assert request_schema["required"] == [
        "email",
        "password",
        "verification_code",
        "username",
    ]
    assert paths["/api/admin/users"]["get"]["operationId"] == "listUsers"
    assert paths["/api/admin/users/{user_id}"]["delete"]["operationId"] == (
        "deleteUser"
    )
    assert paths["/api/admin/users/{user_id}"]["delete"]["responses"]["204"] == {
        "description": "Successful Response"
    }
    assert paths["/api/admin/providers"]["get"]["operationId"] == (
        "listProviderCatalogEntries"
    )
    assert paths["/api/admin/providers"]["post"]["responses"]["201"]["headers"][
        "Location"
    ]
    assert paths["/api/users/me"]["patch"]["operationId"] == "updateCurrentUser"
    avatar_path = paths["/api/users/me/avatar"]
    assert avatar_path["put"]["operationId"] == "uploadCurrentUserAvatar"
    assert avatar_path["delete"]["operationId"] == "deleteCurrentUserAvatar"
    assert avatar_path["get"]["operationId"] == "getCurrentUserAvatar"
    assert (
        avatar_path["put"]["requestBody"]["content"]["application/octet-stream"][
            "schema"
        ]["format"]
        == "binary"
    )
    assert paths["/api/app/v1/auth/register"]["post"]["operationId"] == (
        "registerNativeUser"
    )
    assert (
        paths["/api/app/v1/auth/registration-code/verify"]["post"]["operationId"]
        == "verifyNativeRegistrationCode"
    )
    assert paths["/api/app/v1/auth/login"]["post"]["operationId"] == ("loginNativeUser")
    assert paths["/api/app/v1/auth/refresh"]["post"]["operationId"] == (
        "refreshNativeSession"
    )
    assert paths["/api/app/v1/auth/logout"]["post"]["operationId"] == (
        "logoutNativeSession"
    )
    native_response_schema = paths["/api/app/v1/auth/login"]["post"]["responses"][
        "200"
    ]["content"]["application/json"]["schema"]
    assert native_response_schema == {
        "$ref": "#/components/schemas/NativeSessionResponse"
    }
    assert schema["components"]["securitySchemes"]["NativeBearerAuth"] == {
        "type": "http",
        "scheme": "bearer",
    }


def test_native_openapi_excludes_browser_and_admin_contracts() -> None:
    schema = build_native_openapi()

    assert set(schema["paths"]) == {
        "/api/app/v1/auth/register",
        "/api/app/v1/auth/registration-code",
        "/api/app/v1/auth/registration-code/verify",
        "/api/app/v1/auth/login",
        "/api/app/v1/auth/me",
        "/api/app/v1/auth/refresh",
        "/api/app/v1/auth/logout",
    }
    assert "NativeBearerAuth" in schema["components"]["securitySchemes"]
    assert "ManagedUserPageResponse" not in schema["components"]["schemas"]
