from __future__ import annotations

import httpx

from app.providers.base import (
    ChatRequest,
    ChatResponse,
    ProviderAdapter,
    ProviderError,
    ProviderRateLimited,
    ProviderUnavailable,
)


class OpenAICompatibleAdapter:
    """Adapter for providers exposing the OpenAI chat-completions wire format."""

    def __init__(
        self,
        *,
        provider_name: str,
        base_url: str,
        api_key: str,
        timeout_seconds: float = 45.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.provider_name = provider_name
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.client = client

    async def complete(self, request: ChatRequest) -> ChatResponse:
        if not self.api_key:
            raise ProviderError("Provider credentials are not configured")
        payload: dict = {
            "model": request.model,
            "messages": [
                {"role": message.role, "content": message.content}
                for message in request.messages
            ],
            "max_tokens": request.max_output_tokens,
        }
        if request.temperature is not None:
            payload["temperature"] = request.temperature

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        try:
            if self.client is not None:
                response = await self.client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers=headers,
                    timeout=self.timeout_seconds,
                )
            else:
                async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                    response = await client.post(
                        f"{self.base_url}/chat/completions",
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
            choice = data["choices"][0]
            output_text = choice["message"]["content"]
            if isinstance(output_text, list):
                output_text = "".join(
                    part.get("text", "") for part in output_text if isinstance(part, dict)
                )
            usage = data.get("usage") or {}
            return ChatResponse(
                provider=self.provider_name,
                model=data.get("model") or request.model,
                output_text=str(output_text or ""),
                input_tokens=usage.get("prompt_tokens"),
                output_tokens=usage.get("completion_tokens"),
                request_id=data.get("id"),
            )
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise ProviderError("Provider returned an unsupported response format") from exc
