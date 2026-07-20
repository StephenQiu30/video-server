from __future__ import annotations

from src.main import create_app


def test_openapi_keeps_the_frozen_video_contract() -> None:
    schema = create_app().openapi()

    expected_operation_ids = {
        ("post", "/api/v1/media/inspect"): "inspectMedia",
        ("post", "/api/v1/downloads"): "createDownload",
        ("get", "/api/v1/downloads/{job_id}"): "getDownload",
        ("post", "/api/v1/downloads/{job_id}/download-url"): "createDownloadUrl",
        ("get", "/health/live"): "getLiveness",
        ("get", "/health/ready"): "getReadiness",
    }

    for (method, path), operation_id in expected_operation_ids.items():
        operation = schema["paths"][path][method]
        assert operation["operationId"] == operation_id
        assert "HTTPValidationError" not in str(operation.get("responses", {}))

    assert "/healthz" in schema["paths"]
    assert "ProblemDetails" in str(schema["components"]["schemas"])
    assert '"code"' not in str(schema)
    assert '"data"' not in str(schema)
