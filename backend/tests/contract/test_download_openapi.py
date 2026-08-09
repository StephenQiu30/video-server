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
        "/api/admin/downloads/analytics",
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


def test_admin_download_analytics_openapi_is_bounded_and_safe(
    tmp_path: Path,
) -> None:
    app = create_app(Settings(app_env="test", frontend_dist_dir=tmp_path / "none"))
    schema = app.openapi()
    operation = schema["paths"]["/api/admin/downloads/analytics"]["get"]

    assert operation["operationId"] == "getDownloadAnalytics"
    days = next(item for item in operation["parameters"] if item["name"] == "days")
    assert days["required"] is False
    assert days["schema"]["minimum"] == 7
    assert days["schema"]["maximum"] == 365
    assert days["schema"]["default"] == 30
    response = operation["responses"]["200"]["content"]["application/json"]["schema"]
    assert response == {"$ref": "#/components/schemas/DownloadAnalyticsResponse"}
    components = schema["components"]["schemas"]
    analytics_contract = "".join(
        str(components[name])
        for name in (
            "DownloadAnalyticsResponse",
            "DownloadAnalyticsSummaryResponse",
            "DownloadAnalyticsDailyResponse",
            "DownloadAnalyticsSourceResponse",
        )
    )
    assert all(
        sensitive not in analytics_contract
        for sensitive in ("owner_hash", "url", "provider_hints", "error_message")
    )
    success_rate = components["DownloadAnalyticsSummaryResponse"]["properties"][
        "success_rate"
    ]
    assert success_rate["minimum"] == 0
    assert success_rate["maximum"] == 100


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
