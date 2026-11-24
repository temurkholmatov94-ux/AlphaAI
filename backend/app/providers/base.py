from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class ChatMessage:
    role: str
    content: str


@dataclass(frozen=True)
class ChatRequest:
    model: str
    messages: list[ChatMessage]
    max_output_tokens: int = 1024
    temperature: float | None = None


@dataclass(frozen=True)
class ChatResponse:
    provider: str
    model: str
    output_text: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    request_id: str | None = None
    raw_metadata: dict = field(default_factory=dict)


class ProviderError(Exception):
    """Safe, provider-neutral error. Never include credentials or raw request bodies."""

    def __init__(self, message: str, *, retryable: bool = False, status_code: int | None = None):
        super().__init__(message)
        self.retryable = retryable
        self.status_code = status_code


class ProviderNotConfigured(ProviderError):
    pass


class ProviderRateLimited(ProviderError):
    pass


class ProviderUnavailable(ProviderError):
    pass


class ProviderAdapter(Protocol):
    provider_name: str

    async def complete(self, request: ChatRequest) -> ChatResponse:
        ...
