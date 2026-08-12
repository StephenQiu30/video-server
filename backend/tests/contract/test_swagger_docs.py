from pathlib import Path

from app.core.config import Settings
from app.main import create_app
from fastapi.testclient import TestClient


def test_swagger_ui_and_openapi_contract_are_available(tmp_path: Path) -> None:
    app = create_app(Settings(app_env="test", frontend_dist_dir=tmp_path / "none"))

    with TestClient(app) as client:
        docs = client.get("/docs")
        schema_response = client.get("/openapi.json")

    assert docs.status_code == 200
    assert "Swagger UI" in docs.text
    assert schema_response.status_code == 200

    schema = schema_response.json()
    assert schema["info"]["title"] == "视频下载与分析服务 API"
    assert {tag["name"] for tag in schema["tags"]} == {
        "system",
        "auth",
        "users",
        "admin",
        "inspections",
        "providers",
        "downloads",
        "analyses",
    }
    assert all(not path.startswith("/api/v1") for path in schema["paths"])

    operations = {
        operation["operationId"]: operation
        for path_item in schema["paths"].values()
        for method, operation in path_item.items()
        if method in {"get", "post", "put", "patch", "delete"}
    }
    assert set(operations) == {
        "getLiveness",
        "getReadiness",
        "registerUser",
        "loginUser",
        "getCurrentUser",
        "refreshUserSession",
        "logoutUser",
        "updateCurrentUser",
        "listUsers",
        "updateUserAccess",
        "getDownloadAnalytics",
        "listProviderCatalogEntries",
        "createProviderCatalogEntry",
        "updateProviderCatalogEntry",
        "deleteProviderCatalogEntry",
        "inspectMedia",
        "getInspection",
        "listProviders",
        "createDownload",
        "getDownload",
        "getDownloadHistory",
        "cancelDownload",
        "retryDownload",
        "issueDownloadUrl",
        "listAnalysisSkills",
        "createAnalysis",
        "getAnalysis",
        "getLatestDownloadAnalysis",
        "exportAnalysisMarkdown",
        "exportAnalysisReport",
        "cancelAnalysis",
        "retryAnalysis",
        "deleteAnalysis",
    }
    assert all(len(operation["tags"]) == 1 for operation in operations.values())

    validation_response = schema["paths"]["/api/downloads"]["post"]["responses"]["422"]
    assert validation_response["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/ProblemDetails"
    }
