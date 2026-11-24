from __future__ import annotations

from dataclasses import dataclass

from app.config import Settings
from app.providers.anthropic import AnthropicProvider
from app.providers.base import ChatMessage, ChatResult, ProviderError
from app.providers.openai_compatible import OpenAICompatibleProvider


@dataclass(frozen=True)
class ModelRoute:
    public_model_id: str
    provider_name: str
    upstream_model_id: str


class ProviderGateway:
    """Server-side provider router. Never returns or logs provider credentials."""

    def __init__(self, settings: Settings, *, http_client=None):
        self._providers = {}
        self._routes: dict[str, ModelRoute] = {}

        if settings.openai_api_key:
            self._providers["openai"] = OpenAICompatibleProvider(
                api_key=settings.openai_api_key,
                base_url=settings.openai_base_url,
                http_client=http_client,
            )
        if settings.anthropic_api_key:
            self._providers["anthropic"] = AnthropicProvider(
                api_key=settings.anthropic_api_key,
                base_url=settings.anthropic_base_url,
                http_client=http_client,
            )

        for item in settings.alphaai_model_routes:
            # Format: public-id=provider:upstream-model
            public_id, separator, target = item.partition("=")
            provider, target_separator, upstream_id = target.partition(":")
            if not separator or not target_separator or not public_id or not upstream_id:
                raise ValueError(f"Invalid ALPHAAI_MODEL_ROUTES entry: {item!r}")
            if provider not in {"openai", "anthropic"}:
                raise ValueError(f"Unsupported provider in model route: {provider}")
            if provider not in self._providers:
                # A route without configured credentials must not appear runnable.
                continue
            if public_id in self._routes:
                raise ValueError(f"Duplicate public model route: {public_id}")
            self._routes[public_id] = ModelRoute(public_id, provider, upstream_id)

    @property
    def available_models(self) -> list[str]:
        return sorted(self._routes)

    async def chat(
        self,
        *,
        model: str,
        messages: list[ChatMessage],
        max_tokens: int = 1024,
        temperature: float = 0.2,
    ) -> ChatResult:
        route = self._routes.get(model)
        if route is None:
            raise ProviderError("model_unavailable", "Requested model is not configured", 404)
        provider = self._providers.get(route.provider_name)
        if provider is None:
            raise ProviderError("provider_unavailable", "Provider is not configured", 503)
        return await provider.chat(
            model=route.upstream_model_id,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
