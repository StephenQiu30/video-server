from __future__ import annotations

import asyncio
import json

import httpx
import pytest
from app.integrations.ai_api.catalog import OpenRouterModelCatalog
from app.integrations.ai_api.chat import ChatCompletionsModel
from app.integrations.ai_cli.errors import AnalysisCliError
from langchain_core.messages import HumanMessage

SCHEMA = {
    "type": "object",
    "properties": {"ok": {"type": "boolean"}},
    "required": ["ok"],
    "additionalProperties": False,
}


def catalog_payload(*, image: bool = True, structured: bool = True) -> dict:
    return {
        "data": [
            {
                "id": "vendor/model",
                "name": "Model",
                "context_length": 10000,
                "architecture": {
                    "input_modalities": ["text", "image"] if image else ["text"],
                    "output_modalities": ["text"],
                },
                "supported_parameters": ["structured_outputs"] if structured else [],
            }
        ]
    }


def completion() -> dict:
    return {
        "choices": [{"finish_reason": "stop", "message": {"content": '{"ok":true}'}}]
    }


async def call(model: ChatCompletionsModel, *, image: bool = False) -> object:
    content = [{"type": "text", "text": "Analyze"}]
    if image:
        content.append(
            {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,AA=="}}
        )
    return await model.with_structured_output(
        SCHEMA, method="json_mode", include_raw=False
    ).ainvoke([HumanMessage(content=content)])


@pytest.mark.asyncio
async def test_openrouter_routes_only_to_capable_endpoints_without_fallback() -> None:
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path.endswith("/models"):
            assert "authorization" not in request.headers
            return httpx.Response(200, json=catalog_payload())
        payload = json.loads(request.content)
        assert payload["model"] == "vendor/model"
        assert payload["provider"] == {
            "require_parameters": True,
            "allow_fallbacks": False,
        }
        assert payload["response_format"]["json_schema"]["schema"] == SCHEMA
        assert payload["response_format"]["json_schema"]["strict"] is True
        assert request.headers["authorization"] == "Bearer controlled-secret"
        return httpx.Response(200, json=completion())

    transport = httpx.MockTransport(handler)
    model = ChatCompletionsModel(
        base_url="https://openrouter.ai/api/v1",
        model="vendor/model",
        api_key="controlled-secret",
        timeout_seconds=2,
        maximum_bytes=4096,
        catalog=OpenRouterModelCatalog(transport=transport),
        transport=transport,
    )
    assert await call(model, image=True) == {"ok": True}
    assert len(requests) == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("image,structured", [(False, True), (True, False)])
async def test_incapable_model_is_rejected_before_paid_request(
    image: bool, structured: bool
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/models")
        return httpx.Response(
            200, json=catalog_payload(image=image, structured=structured)
        )

    transport = httpx.MockTransport(handler)
    model = ChatCompletionsModel(
        base_url="https://openrouter.ai/api/v1",
        model="vendor/model",
        api_key="secret",
        timeout_seconds=2,
        maximum_bytes=4096,
        catalog=OpenRouterModelCatalog(transport=transport),
        transport=transport,
    )
    with pytest.raises(AnalysisCliError, match="analysis_cli_unsupported"):
        await call(model, image=True)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status,code",
    [
        (401, "analysis_cli_not_authenticated"),
        (402, "analysis_provider_usage_limited"),
        (429, "analysis_provider_rate_limited"),
        (503, "analysis_cli_failed"),
    ],
)
async def test_errors_are_sanitized_and_not_retried(status: int, code: str) -> None:
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            status, json={"error": {"message": "secret upstream payload"}}
        )

    model = ChatCompletionsModel(
        base_url="https://api.example.com/v1",
        model="model",
        api_key="secret",
        timeout_seconds=2,
        maximum_bytes=4096,
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(AnalysisCliError, match=code) as caught:
        await call(model)
    assert "secret" not in str(caught.value)
    assert caught.value.__cause__ is None
    assert len(requests) == 1


@pytest.mark.asyncio
async def test_generic_api_uses_json_object_and_never_sends_router_extensions() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/chat/completions"
        payload = json.loads(request.content)
        assert payload["response_format"] == {"type": "json_object"}
        assert "provider" not in payload
        return httpx.Response(200, json=completion())

    model = ChatCompletionsModel(
        base_url="https://api.example.com/v1",
        model="model",
        api_key="secret",
        timeout_seconds=2,
        maximum_bytes=4096,
        transport=httpx.MockTransport(handler),
    )
    assert await call(model) == {"ok": True}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "body", [b"x" * 4097, b'{"choices":[]}', b'{"error":{"code":429}}', b"not json"]
)
async def test_bounded_or_invalid_upstream_output_fails(body: bytes) -> None:
    model = ChatCompletionsModel(
        base_url="https://api.example.com/v1",
        model="model",
        api_key="secret",
        timeout_seconds=2,
        maximum_bytes=4096,
        transport=httpx.MockTransport(lambda _: httpx.Response(200, content=body)),
    )
    with pytest.raises(AnalysisCliError):
        await call(model)


@pytest.mark.asyncio
async def test_cancellation_propagates() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        raise asyncio.CancelledError

    model = ChatCompletionsModel(
        base_url="https://api.example.com/v1",
        model="model",
        api_key="secret",
        timeout_seconds=2,
        maximum_bytes=4096,
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(asyncio.CancelledError):
        await call(model)


@pytest.mark.asyncio
async def test_redirect_never_forwards_credentials() -> None:
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(307, headers={"Location": "https://other.example/steal"})

    model = ChatCompletionsModel(
        base_url="https://api.example.com/v1",
        model="model",
        api_key="secret",
        timeout_seconds=2,
        maximum_bytes=4096,
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(AnalysisCliError):
        await call(model)
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_total_timeout_is_bounded() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        await asyncio.sleep(1)
        return httpx.Response(200, json=completion())

    model = ChatCompletionsModel(
        base_url="https://api.example.com/v1",
        model="model",
        api_key="secret",
        timeout_seconds=0.01,
        maximum_bytes=4096,
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(AnalysisCliError, match="analysis_cli_timeout"):
        await call(model)
