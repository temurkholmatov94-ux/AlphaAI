from dataclasses import dataclass

from app.config import Settings, get_settings
from app.providers.anthropic import AnthropicAdapter
from app.providers.base import ProviderAdapter, ProviderNotConfigured
from app.providers.openai_compatible import OpenAICompatibleAdapter


@dataclass(frozen=True)
class ProviderDescriptor:
    name: str
    protocol: str
    configured: bool


class ProviderRegistry:
    def __init__(self, adapters: dict[str, ProviderAdapter]) -> None:
        self._adapters = dict(adapters)

    def get(self, provider_name: str) -> ProviderAdapter:
        try:
            return self._adapters[provider_name.lower()]
        except KeyError as exc:
            raise ProviderNotConfigured(
                f"Provider '{provider_name}' is not configured"
            ) from exc

    def descriptors(self) -> list[ProviderDescriptor]:
        return [
            ProviderDescriptor(name=name, protocol=protocol, configured=name in self._adapters)
            for name, protocol in (
                ("openai", "openai-chat-completions"),
                ("anthropic", "anthropic-messages"),
                ("xai", "openai-chat-completions"),
            )
        ]


def build_provider_registry(settings: Settings | None = None) -> ProviderRegistry:
    settings = settings or get_settings()
    adapters: dict[str, ProviderAdapter] = {}

    if settings.openai_api_key:
        adapters["openai"] = OpenAICompatibleAdapter(
            provider_name="openai",
            base_url=settings.openai_base_url,
            api_key=settings.openai_api_key,
        )
    if settings.xai_api_key:
        adapters["xai"] = OpenAICompatibleAdapter(
            provider_name="xai",
            base_url=settings.xai_base_url,
            api_key=settings.xai_api_key,
        )
    if settings.anthropic_api_key:
        adapters["anthropic"] = AnthropicAdapter(
            api_key=settings.anthropic_api_key,
            base_url=settings.anthropic_base_url,
        )

    return ProviderRegistry(adapters)
