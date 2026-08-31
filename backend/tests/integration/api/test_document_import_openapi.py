from pathlib import Path

from app.core.config import Settings
from app.main import create_app


def test_document_openapi_operations_are_stable(tmp_path: Path) -> None:
    schema = create_app(
        Settings(app_env="test", frontend_dist_dir=tmp_path / "none")
    ).openapi()
    paths = schema["paths"]
    assert paths["/api/documents"]["post"]["operationId"] == "createDocumentImport"
    assert paths["/api/documents"]["get"]["operationId"] == "listDocuments"
    assert paths["/api/documents/{document_id}"]["get"]["operationId"] == (
        "getDocumentImport"
    )
    assert paths["/api/documents/{document_id}"]["delete"]["operationId"] == (
        "deleteDocument"
    )
    assert (
        paths["/api/documents/{document_id}/upload-sessions"]["post"]["operationId"]
        == "createDocumentUploadSession"
    )
    assert (
        paths["/api/documents/{document_id}/complete"]["post"]["operationId"]
        == "completeDocumentImport"
    )
    assert paths["/api/documents/{document_id}/cancel"]["post"]["operationId"] == (
        "cancelDocumentImport"
    )
    assert "object_key" not in str(paths).casefold()
    response = schema["components"]["schemas"]["DocumentDetailResponse"]
    preview_shapes = response["properties"]["preview"]["anyOf"]
    assert any(shape.get("maxLength") == 1_000_000 for shape in preview_shapes)
    assert {"preview", "preview_truncated", "parse_summary"}.issubset(
        response["required"]
    )
    summary = schema["components"]["schemas"]["DocumentParseSummaryResponse"]
    assert {
        "page_count",
        "paragraph_count",
        "heading_count",
        "list_item_count",
        "table_count",
        "dialogue_block_count",
    } <= set(summary["properties"])
