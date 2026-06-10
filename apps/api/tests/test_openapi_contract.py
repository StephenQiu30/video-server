from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app


def _openapi() -> dict:
    response = TestClient(create_app()).get("/openapi.json")
    assert response.status_code == 200
    return response.json()


def _success_schema(openapi: dict, method: str, path: str, status_code: str = "200") -> dict:
    return openapi["paths"][path][method]["responses"][status_code]["content"]["application/json"]["schema"]


def _ref_name(schema: dict) -> str:
    return schema["$ref"].rsplit("/", 1)[-1]


def test_swagger_redoc_and_openapi_entrypoints_are_available() -> None:
    client = TestClient(create_app())

    assert client.get("/openapi.json").status_code == 200
    assert client.get("/docs").status_code == 200
    assert client.get("/redoc").status_code == 200


def test_openapi_documents_core_video_downloader_response_models() -> None:
    openapi = _openapi()
    schemas = openapi["components"]["schemas"]

    for schema_name in [
        "Token",
        "UserRead",
        "ParseResponse",
        "TaskRead",
        "TaskEventRead",
        "DownloadLinkResponse",
        "HealthResponse",
        "ReadinessResponse",
        "AdminMetricsResponse",
    ]:
        assert schema_name in schemas

    assert _ref_name(_success_schema(openapi, "post", "/api/parse")) == "ParseResponse"
    assert _success_schema(openapi, "get", "/api/tasks")["items"]["$ref"].endswith("/TaskRead")
    assert _ref_name(_success_schema(openapi, "get", "/api/auth/me")) == "UserRead"
    assert _ref_name(_success_schema(openapi, "get", "/api/tasks/{task_id}/download-link")) == "DownloadLinkResponse"
    assert _ref_name(_success_schema(openapi, "get", "/ready")) == "ReadinessResponse"
    assert _ref_name(_success_schema(openapi, "get", "/api/admin/metrics")) == "AdminMetricsResponse"


def test_openapi_video_format_schema_includes_watermark_hint() -> None:
    openapi = _openapi()
    video_format = openapi["components"]["schemas"]["VideoFormat"]

    assert "watermark_hint" in video_format["properties"], (
        "VideoFormat schema must include watermark_hint field"
    )
    prop = video_format["properties"]["watermark_hint"]
    # Should be an optional string (anyOf with string + null, or nullable string)
    assert prop.get("type") == "string" or prop.get("nullable") is True or "anyOf" in prop


def test_openapi_documents_non_json_runtime_responses() -> None:
    openapi = _openapi()

    pdf_response = openapi["paths"]["/api/tasks/{task_id}/pdf"]["get"]["responses"]["200"]
    assert pdf_response["content"]["application/pdf"]["schema"] == {
        "type": "string",
        "format": "binary",
    }

    stream_response = openapi["paths"]["/api/tasks/stream"]["get"]["responses"]["200"]
    assert stream_response["content"]["text/event-stream"]["schema"]["type"] == "string"

    oauth_callback_responses = openapi["paths"]["/api/auth/github/callback"]["get"]["responses"]
    assert "307" in oauth_callback_responses
    assert "200" not in oauth_callback_responses


def test_openapi_export_and_frontend_collaboration_assets_exist() -> None:
    export_script = Path("scripts/export_openapi.py")
    collaboration_doc = Path("docs/operations/001-OpenAPI契约与前端生成协作.md")

    assert export_script.exists()
    assert collaboration_doc.exists()

    text = collaboration_doc.read_text(encoding="utf-8")
    assert "scripts/export_openapi.py" in text
    assert "video-web" in text
    assert "npm run api:generate" in text
