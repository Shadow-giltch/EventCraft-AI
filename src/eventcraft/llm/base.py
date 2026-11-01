"""Base abstractions and response types for language model providers."""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class LLMResponse:
    """Standardized response container returned by all LLM client implementations."""

    content: str
    source: str  # "ai" or "template"
    latency_ms: int
    tokens_used: int | None = None


class LLMClient(Protocol):
    """Protocol defining interface for language model client implementations."""

    async def generate(
        self,
        prompt: str,
        temperature: float = 0.2,
        max_output_tokens: int = 1024,
    ) -> LLMResponse:
        """Generate structured text matching prompt and constraints."""
        ...
