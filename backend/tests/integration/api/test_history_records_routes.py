from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.api.deps import get_current_user, get_history_record_service
from app.main import create_app
from app.services.history_records import HistoryRecordKind, HistoryRecordPage
from fastapi.testclient import TestClient
from tests.integration.api.test_analysis_routes import TEST_USER


def test_history_filter_contract_and_validation():
    service = SimpleNamespace(list=AsyncMock(return_value=HistoryRecordPage((), None)))
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: TEST_USER
    app.dependency_overrides[get_history_record_service] = lambda: service
    client = TestClient(app)
    response = client.get(
        "/api/download-intents/history/records",
        params=[
            ("record_type", "document_parse"),
            ("record_type", "screenplay_analysis"),
            ("q", "  剧本  "),
            ("created_from", "2026-09-24T00:00:00Z"),
        ],
    )
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    filters = service.list.call_args.kwargs["filters"]
    assert filters.record_types == (
        HistoryRecordKind.DOCUMENT_PARSE,
        HistoryRecordKind.SCREENPLAY_ANALYSIS,
    )
    assert filters.q == "剧本"
    assert filters.created_from == datetime(2026, 9, 24, tzinfo=UTC)
    for params in [
        {"limit": 51},
        {"before_id": str(TEST_USER.id)},
        {"created_from": "2026-09-24T00:00:00"},
        {"record_type": "parse", "skill_id": "test"},
        {"created_from": "2026-09-25T00:00:00Z", "created_to": "2026-09-24T00:00:00Z"},
    ]:
        assert (
            client.get(
                "/api/download-intents/history/records", params=params
            ).status_code
            == 422
        )


def test_history_openapi_discriminates_all_record_types():
    schema = create_app().openapi()["components"]["schemas"]
    item = schema["HistoryRecordPageResponse"]["properties"]["items"]["items"]
    assert set(item["discriminator"]["mapping"]) == {
        kind.value for kind in HistoryRecordKind
    }
    assert (
        schema["DocumentParseHistoryRecordResponse"]["properties"]["record_type"][
            "const"
        ]
        == "document_parse"
    )
    assert (
        "owner_hash"
        not in schema["ScreenplayAnalysisHistoryRecordResponse"]["properties"]
    )
