import json

import httpx
import pytest

from app.config import Settings
from app.providers import ChatMessage, ChatRequest, ProviderError, ProviderGateway
from app.providers.anthropic import AnthropicAdapter
from app.providers.openai_compatible import OpenAICompatibleAdapter
from app.providers.registry import build_provider_registry


@pytest.mark.asyncio
async def test_openai_compatible_adapter_maps_request_and_usage():
    seen = {}

    def handler(request):
        seen["authorization"] = request.headers.get("authorization")
        seen["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl-test",
                "model": "upstream-model",
                "choices": [{"message": {"role": "assistant", "content": "Hello"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 4, "completion_tokens": 2, "total_tokens": 6},
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        adapter = OpenAICompatibleAdapter(
            provider_name="openai",
            api_key="test-secret",
            base_url="https://api.example.test/v1",
            client=client,
        )
        result = await adapter.complete(
            ChatRequest(
                model="upstream-model",
                messages=[ChatMessage(role="user", content="Hi")],
                max_output_tokens=17,
                temperature=0.1,
            )
        )

    assert result.output_text == "Hello"
    assert result.input_tokens == 4
    assert result.output_tokens == 2
    assert seen["authorization"] == "Bearer test-secret"
    assert seen["body"]["max_tokens"] == 17


@pytest.mark.asyncio
async def test_anthropic_adapter_maps_system_message_and_usage():
    seen = {}

    def handler(request):
        seen["version"] = request.headers.get("anthropic-version")
        seen["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "id": "msg_test",
                "model": "claude-test",
                "content": [{"type": "text", "text": "Safe answer"}],
                "stop_reason": "end_turn",
                "usage": {"input_tokens": 9, "output_tokens": 3},
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        adapter = AnthropicAdapter(
            api_key="test-secret",
            base_url="https://api.example.test",
            client=client,
        )
        result = await adapter.complete(
            ChatRequest(
                model="claude-test",
                messages=[
                    ChatMessage(role="system", content="Be precise"),
                    ChatMessage(role="user", content="Explain"),
                ],
            )
        )

    assert result.output_text == "Safe answer"
    assert result.input_tokens == 9
    assert result.output_tokens == 3
    assert seen["version"] == "2023-06-01"
    assert seen["body"]["system"] == "Be precise"
    assert seen["body"]["messages"][0]["role"] == "user"


@pytest.mark.asyncio
async def test_gateway_routes_only_explicitly_configured_models():
    settings = Settings(
        app_env="test",
        alphaai_secret_key="test-secret-key-with-at-least-32-characters",
        openai_api_key="test-provider-key",
        alphaai_model_routes=["alpha-fast=openai:gpt-test"],
    )
    gateway = ProviderGateway(settings)
    assert gateway.available_models == ["alpha-fast"]

    with pytest.raises(ProviderError) as error:
        await gateway.chat(
            model="unlisted-model",
            messages=[ChatMessage(role="user", content="Hi")],
        )
    assert error.value.status_code == 404


@pytest.mark.asyncio
async def test_provider_http_error_does_not_leak_credentials():
    def handler(request):
        return httpx.Response(401, json={"error": {"message": "invalid key"}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        adapter = OpenAICompatibleAdapter(
            provider_name="openai",
            api_key="top-secret-key",
            base_url="https://api.example.test/v1",
            client=client,
        )
        with pytest.raises(ProviderError) as error:
            await adapter.complete(
                ChatRequest(model="m", messages=[ChatMessage(role="user", content="Hi")])
            )

    assert error.value.status_code == 401
    assert "top-secret-key" not in str(error.value)


def test_provider_registry_only_reports_credentials_as_configured():
    settings = Settings(
        openai_api_key="openai-test",
        xai_api_key=None,
        anthropic_api_key=None,
    )
    descriptors = build_provider_registry(settings).descriptors()
    configured = {item.name for item in descriptors if item.configured}
    assert configured == {"openai"}
