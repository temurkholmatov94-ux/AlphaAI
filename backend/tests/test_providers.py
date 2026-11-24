import httpx
import pytest

from app.config import Settings
from app.providers.anthropic import AnthropicProvider
from app.providers.base import ChatMessage, ProviderError
from app.providers.openai_compatible import OpenAICompatibleProvider
from app.providers.service import ProviderGateway


@pytest.mark.asyncio
async def test_openai_compatible_adapter_maps_chat_request_and_usage():
    seen = {}

    def handler(request):
        seen["authorization"] = request.headers.get("authorization")
        seen["body"] = __import__("json").loads(request.content)
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl-test",
                "model": "upstream-model",
                "choices": [{"message": {"role": "assistant", "content": "Hello"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 4, "completion_tokens": 2, "total_tokens": 6},
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = OpenAICompatibleProvider(api_key="test-secret", base_url="https://api.example.test/v1", http_client=client)
    result = await provider.chat(
        model="upstream-model",
        messages=[ChatMessage(role="user", content="Hi")],
        max_tokens=17,
        temperature=0.1,
    )
    assert result.content == "Hello"
    assert result.input_tokens == 4
    assert result.output_tokens == 2
    assert seen["authorization"] == "Bearer test-secret"
    assert seen["body"]["max_tokens"] == 17
    await client.aclose()


@pytest.mark.asyncio
async def test_anthropic_adapter_maps_system_message_and_usage():
    seen = {}

    def handler(request):
        seen["version"] = request.headers.get("anthropic-version")
        seen["body"] = __import__("json").loads(request.content)
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

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = AnthropicProvider(api_key="test-secret", base_url="https://api.example.test", http_client=client)
    result = await provider.chat(
        model="claude-test",
        messages=[
            ChatMessage(role="system", content="Be precise"),
            ChatMessage(role="user", content="Explain"),
        ],
    )
    assert result.content == "Safe answer"
    assert result.input_tokens == 9
    assert result.output_tokens == 3
    assert seen["version"] == "2023-06-01"
    assert seen["body"]["system"] == "Be precise"
    assert seen["body"]["messages"][0]["role"] == "user"
    await client.aclose()


@pytest.mark.asyncio
async def test_provider_gateway_routes_only_explicitly_configured_models():
    settings = Settings(
        app_env="test",
        alphaai_secret_key="test-secret-key-with-at-least-32-characters",
        openai_api_key="test-provider-key",
        alphaai_model_routes=["alpha-fast=openai:gpt-test"],
    )
    gateway = ProviderGateway(settings)
    assert gateway.available_models == ["alpha-fast"]
    with pytest.raises(ProviderError) as error:
        await gateway.chat(model="unlisted-model", messages=[ChatMessage(role="user", content="Hi")])
    assert error.value.code == "model_unavailable"


@pytest.mark.asyncio
async def test_provider_http_error_does_not_leak_credentials():
    def handler(request):
        return httpx.Response(401, json={"error": {"message": "invalid key"}})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = OpenAICompatibleProvider(api_key="top-secret-key", base_url="https://api.example.test/v1", http_client=client)
    with pytest.raises(ProviderError) as error:
        await provider.chat(model="m", messages=[ChatMessage(role="user", content="Hi")])
    assert error.value.status_code == 502
    assert "top-secret-key" not in str(error.value)
    await client.aclose()
