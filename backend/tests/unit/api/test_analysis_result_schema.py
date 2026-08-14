from app.api.schemas.analysis_results import ANALYSIS_RESULT_RESPONSE_ADAPTER
from tests.unit.domain.analysis.screenplay_factories import (
    screenplay_analysis_result,
    screenplay_rewrite_result,
)


def test_screenplay_analysis_public_result_uses_discriminator() -> None:
    response = ANALYSIS_RESULT_RESPONSE_ADAPTER.validate_python(
        screenplay_analysis_result()
    )

    payload = ANALYSIS_RESULT_RESPONSE_ADAPTER.dump_python(response, mode="json")
    assert payload["kind"] == "screenplay_analysis"
    assert payload["scenes"][0]["source_scene_id"] == "scene-1"


def test_screenplay_rewrite_public_result_omits_private_chunks() -> None:
    response = ANALYSIS_RESULT_RESPONSE_ADAPTER.validate_python(
        screenplay_rewrite_result()
    )

    payload = ANALYSIS_RESULT_RESPONSE_ADAPTER.dump_python(response, mode="json")
    assert payload["kind"] == "screenplay_rewrite"
    assert payload["target_language"] == "en-US"
    assert "chunks" not in payload
    assert (
        "rewritten_text"
        not in ANALYSIS_RESULT_RESPONSE_ADAPTER.dump_json(response).decode()
    )
