from __future__ import annotations

from dataclasses import dataclass

from app.config import Settings
from app.providers.base import ChatMessage, ChatRequest, ChatResponse, ProviderError
from app.providers.registry import ProviderRegistry, build_provider_registry


@dataclass(frozen=True)
class ModelRoute:
    public_model_id: str
    provider_name: str
    upstream_model_id: str


class ProviderGateway:
    """Routes approved public model IDs to server-configured provider adapters."""

    def __init__(self, settings: Settings, *, registry: ProviderRegistry | None = None):
        self._registry = registry or build_provider_registry(settings)
        self._routes: dict[str, ModelRoute] = {}

        for item in settings.alphaai_model_routes:
            # Format: public-id=provider:upstream-model
            public_id, separator, target = item.partition("=")
            provider, target_separator, upstream_id = target.partition(":")
            if not separator or not target_separator or not public_id.strip() or not upstream_id.strip():
                raise ValueError(f"Invalid ALPHAAI_MODEL_ROUTES entry: {item!r}")
            public_id = public_id.strip()
            provider = provider.strip().lower()
            upstream_id = upstream_id.strip()
            if provider not in {"openai", "anthropic", "xai"}:
                raise ValueError(f"Unsupported provider in model route: {provider}")
            if public_id in self._routes:
                raise ValueError(f"Duplicate public model route: {public_id}")
            # Keep configured model IDs out of the public catalog until the provider
            # credential is present. Missing credentials are not treated as availability.
            try:
                self._registry.get(provider)
            except ProviderError:
                continue
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
        temperature: float | None = None,
    ) -> ChatResponse:
        route = self._routes.get(model)
        if route is None:
            raise ProviderError("Requested model is not configured", status_code=404)
        adapter = self._registry.get(route.provider_name)
        request = ChatRequest(
            model=route.upstream_model_id,
            messages=messages,
            max_output_tokens=max_tokens,
            temperature=temperature,
        )
        return await adapter.complete(request)
