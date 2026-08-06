from pathlib import Path

from app.core.config import Settings
from app.main import create_app


def test_analysis_openapi_is_current_and_excludes_internal_fields(
    tmp_path: Path,
) -> None:
    schema = create_app(
        Settings(app_env="test", frontend_dist_dir=tmp_path / "none")
    ).openapi()
    paths = schema["paths"]
    create_path = "/api/v1/downloads/{download_id}/analyses"

    assert {
        create_path,
        "/api/v1/analyses/{analysis_id}",
        "/api/v1/analyses/{analysis_id}/cancel",
    } <= paths.keys()
    header = next(
        item
        for item in paths[create_path]["post"]["parameters"]
        if item["name"] == "Idempotency-Key"
    )
    assert header["required"] is True
    components = schema["components"]["schemas"]
    assert components["AnalysisRequest"]["additionalProperties"] is False
    fields = components["AnalysisResponse"]["properties"]
    assert {"artifact_id", "schema_version", "transcript", "provider"}.isdisjoint(
        fields
    )
