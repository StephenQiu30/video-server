from __future__ import annotations

import httpx
import pytest
from app.integrations.ai_api.catalog import OpenRouterModelCatalog
from app.services.ai_model_catalog import ModelCatalogUnavailable
from tests.unit.integrations.ai_api.test_chat import catalog_payload


@pytest.mark.asyncio
async def test_catalog_cache_keeps_capabilities_and_avoids_duplicate_requests() -> None:
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json=catalog_payload())

    catalog = OpenRouterModelCatalog(transport=httpx.MockTransport(handler))
    first = await catalog.list_models()
    assert await catalog.list_models() is first
    assert first[0].supports_analysis(images=True)
    assert len(calls) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", [{}, {"data": [{}]}, {"data": [{"id": "invalid"}]}])
async def test_invalid_catalog_is_unavailable_not_a_fake_capability(
    payload: dict,
) -> None:
    catalog = OpenRouterModelCatalog(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json=payload))
    )
    with pytest.raises(ModelCatalogUnavailable):
        await catalog.list_models()
