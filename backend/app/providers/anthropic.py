from __future__ import annotations

import httpx

from app.providers.base import (
    ChatRequest,
    ChatResponse,
    ProviderError,
    ProviderRateLimited,
    ProviderUnavailable,
)


class AnthropicAdapter:
    """Adapter for Anthropic's Messages API; credentials stay server-side."""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = "https://api.anthropic.com",
        api_version: str = "2023-06-01",
        timeout_seconds: float = 45.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.provider_name = "anthropic"
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.api_version = api_version
        self.timeout_seconds = timeout_seconds
        self.client = client

    async def complete(self, request: ChatRequest) -> ChatResponse:
        if not self.api_key:
            raise ProviderError("Provider credentials are not configured")

        system_messages = [m.content for m in request.messages if m.role == "system"]
        messages = [
            {"role": m.role, "content": m.content}
            for m in request.messages
            if m.role in {"user", "assistant"}
        ]
        if not messages:
            raise ProviderError("At least one user or assistant message is required")

        payload: dict = {
            "model": request.model,
            "max_tokens": request.max_output_tokens,
            "messages": messages,
        }
        if system_messages:
            payload["system"] = "\n\n".join(system_messages)
        if request.temperature is not None:
            payload["temperature"] = request.temperature

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": self.api_version,
            "content-type": "application/json",
        }
        try:
            if self.client is not None:
                response = await self.client.post(
                    f"{self.base_url}/v1/messages",
                    json=payload,
                    headers=headers,
                    timeout=self.timeout_seconds,
                )
            else:
                async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                    response = await client.post(
                        f"{self.base_url}/v1/messages",
                        json=payload,
                        headers=headers,
                    )
        except httpx.TimeoutException as exc:
            raise ProviderUnavailable("Provider request timed out", retryable=True) from exc
        except httpx.RequestError as exc:
            raise ProviderUnavailable("Provider could not be reached", retryable=True) from exc

        if response.status_code == 429:
            raise ProviderRateLimited("Provider rate limit reached", retryable=True, status_code=429)
        if response.status_code in {408, 409, 425} or response.status_code >= 500:
            raise ProviderUnavailable(
                "Provider is temporarily unavailable",
                retryable=True,
                status_code=response.status_code,
            )
        if response.is_error:
            raise ProviderError(
                "Provider rejected the request",
                retryable=False,
                status_code=response.status_code,
            )

        try:
            data = response.json()
            text_parts = [
                part.get("text", "")
                for part in data["content"]
                if part.get("type") == "text"
            ]
            usage = data.get("usage") or {}
            return ChatResponse(
                provider=self.provider_name,
                model=data.get("model") or request.model,
                output_text="".join(text_parts),
                input_tokens=usage.get("input_tokens"),
                output_tokens=usage.get("output_tokens"),
                request_id=data.get("id"),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ProviderError("Provider returned an unsupported response format") from exc
