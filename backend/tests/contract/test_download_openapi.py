from __future__ import annotations

from pathlib import Path

from app.core.config import Settings
from app.main import create_app


def test_download_openapi_exposes_required_routes_and_idempotency(
    tmp_path: Path,
) -> None:
    app = create_app(Settings(app_env="test", frontend_dist_dir=tmp_path / "none"))
    schema = app.openapi()
    paths = schema["paths"]

    assert {
        "/api/inspections",
        "/api/inspections/{inspection_id}",
        "/api/downloads",
        "/api/downloads/{job_id}",
        "/api/downloads/{job_id}/cancel",
        "/api/downloads/{job_id}/download-url",
    } <= paths.keys()
    for path in ("/api/inspections", "/api/downloads"):
        parameters = paths[path]["post"]["parameters"]
        header = next(item for item in parameters if item["name"] == "Idempotency-Key")
        assert header["in"] == "header"
        assert header["required"] is True
    assert paths["/api/inspections"]["post"]["operationId"] == "inspectMedia"
    assert paths["/api/downloads"]["post"]["operationId"] == "createDownload"
    create_response = paths["/api/downloads"]["post"]["responses"]["201"]
    assert create_response["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/DownloadResponse"
    }


def test_request_schemas_forbid_unknown_fields_and_plan_has_no_hints(
    tmp_path: Path,
) -> None:
    app = create_app(Settings(app_env="test", frontend_dist_dir=tmp_path / "none"))
    components = app.openapi()["components"]["schemas"]

    assert components["InspectionRequest"]["additionalProperties"] is False
    assert components["DownloadRequest"]["additionalProperties"] is False
    plan_properties = components["SemanticPlanResponse"]["properties"]
    assert "hints" not in plan_properties
    assert "provider_hints" not in plan_properties
