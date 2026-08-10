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
    create_path = "/api/downloads/{download_id}/analyses"

    assert {
        create_path,
        "/api/analyses/{analysis_id}",
        "/api/analyses/{analysis_id}/cancel",
        "/api/analyses/{analysis_id}/report.docx",
    } <= paths.keys()
    assert paths[create_path]["post"]["operationId"] == "createAnalysis"
    create_response = paths[create_path]["post"]["responses"]["201"]
    assert create_response["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/AnalysisResponse"
    }
    header = next(
        item
        for item in paths[create_path]["post"]["parameters"]
        if item["name"] == "Idempotency-Key"
    )
    assert header["required"] is True
    components = schema["components"]["schemas"]
    assert components["AnalysisRequest"]["additionalProperties"] is False
    fields = components["AnalysisResponse"]["properties"]
    assert "report_markdown" in fields
    assert {"artifact_id", "schema_version", "transcript", "provider"}.isdisjoint(
        fields
    )
    result_fields = components["AnalysisResultResponse"]["properties"]
    assert {
        "media",
        "shot_count",
        "shots",
        "highlights",
        "assets",
        "production_advice",
    } <= set(result_fields)
    shot_fields = components["ShotResponse"]["properties"]
    assert {"narrative_function", "highlight_score"} <= set(shot_fields)
    assert {"provider", "model", "cli_version"}.isdisjoint(result_fields)
    export = paths["/api/analyses/{analysis_id}/report.docx"]["get"]
    assert export["operationId"] == "exportAnalysisReport"
    assert (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        in export["responses"]["200"]["content"]
    )
