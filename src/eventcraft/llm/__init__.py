"""Language model integration, offline fallbacks, caching, and prompt guardrails."""

from eventcraft.llm.base import LLMClient, LLMResponse
from eventcraft.llm.cache import SingleFlightCache
from eventcraft.llm.gemini import GeminiClient, LLMProviderError
from eventcraft.llm.guardrails import clean_text_input, wrap_user_data
from eventcraft.llm.offline import OfflineClient
from eventcraft.llm.parsing import JSONRepairFailedError, parse_and_repair_json
from eventcraft.llm.prompts import (
    OFF_TOPIC_REFUSAL,
    PROMPT_VERSION,
    build_assistant_prompt,
    build_budget_weights_prompt,
    build_ideas_prompt,
)

__all__ = [
    "OFF_TOPIC_REFUSAL",
    "PROMPT_VERSION",
    "GeminiClient",
    "JSONRepairFailedError",
    "LLMClient",
    "LLMProviderError",
    "LLMResponse",
    "OfflineClient",
    "SingleFlightCache",
    "build_assistant_prompt",
    "build_budget_weights_prompt",
    "build_ideas_prompt",
    "clean_text_input",
    "parse_and_repair_json",
    "wrap_user_data",
]
