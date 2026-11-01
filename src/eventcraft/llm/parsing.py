"""Robust JSON parser with single repair attempt for LLM outputs."""

import json
import re
from typing import Any

TRAILING_COMMA_PATTERN = re.compile(r",\s*([}\]])")
CODE_FENCE = "`" * 3
ENVELOPE_KEYS = ("response", "answer", "text")
DEFAULT_MAX_ASSISTANT_LENGTH = 1500


class JSONRepairFailedError(ValueError):
    """Raised when JSON parsing fails after repair attempt."""


class AssistantResponseParsingError(ValueError):
    """Raised when parsing or validating the assistant response fails."""


def _strip_code_fences(text: str) -> str:
    """Remove a leading and trailing markdown code fence, if present."""
    if not text.startswith(CODE_FENCE):
        return text
    lines = text.splitlines()[1:]  # the opening fence line may carry a language tag
    if lines and lines[-1].strip() == CODE_FENCE:
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _extract_envelope(text: str) -> str:
    """Return the outermost {...} span of the text, or the text unchanged."""
    first, last = text.find("{"), text.rfind("}")
    if first != -1 and last > first:
        return text[first : last + 1]
    return text


def _attempt_json_repair(raw: str) -> str:
    """Strip fences, extract the outermost JSON object, and drop trailing commas."""
    text = _extract_envelope(_strip_code_fences(raw.strip()))
    return TRAILING_COMMA_PATTERN.sub(r"\1", text)


def parse_and_repair_json(raw_text: str) -> dict[str, Any]:
    """Parse JSON text, falling back to one cleanup repair attempt."""
    if not raw_text or not raw_text.strip():
        raise JSONRepairFailedError("Empty output cannot be parsed as JSON.")

    try:
        parsed = json.loads(raw_text)
        if isinstance(parsed, dict):
            return parsed
        raise JSONRepairFailedError("JSON root must be an object dictionary.")
    except (json.JSONDecodeError, JSONRepairFailedError):
        repaired = _attempt_json_repair(raw_text)
        try:
            second_attempt = json.loads(repaired)
            if isinstance(second_attempt, dict):
                return second_attempt
            raise JSONRepairFailedError("Repaired JSON root is not a dictionary.")
        except json.JSONDecodeError as err:
            raise JSONRepairFailedError(f"Failed to parse JSON after repair: {err}") from err


def _looks_like_json(text: str) -> bool:
    """Return True when the text is shaped like a JSON object or a JSON string."""
    is_object = text.startswith("{") and text.endswith("}")
    is_string = text.startswith('"') and text.endswith('"')
    return is_object or is_string


def _decode_json_like(text: str) -> dict[str, Any] | str | None:
    """Decode JSON-looking text, trying the raw text first and one repaired copy second."""
    if not _looks_like_json(text):
        return None
    for candidate in (text, _attempt_json_repair(text)):
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue
    return None


def _unwrap_envelope(parsed: dict[str, Any] | str | None, fallback: str) -> str:
    """Pull the answer text out of a decoded envelope, or return the fallback text."""
    if isinstance(parsed, str):
        return parsed.strip()
    if isinstance(parsed, dict):
        for key in ENVELOPE_KEYS:
            value = parsed.get(key)
            if isinstance(value, str):
                return value.strip()
        raise AssistantResponseParsingError(
            "JSON envelope does not contain a valid 'response' string."
        )
    return fallback


def _validate_answer(text: str, max_length: int) -> str:
    """Ensure the answer is non-empty and within the length cap."""
    if not text:
        raise AssistantResponseParsingError("Assistant answer is empty after parsing.")
    if len(text) > max_length:
        raise AssistantResponseParsingError(
            f"Assistant answer length ({len(text)}) exceeds maximum cap ({max_length})."
        )
    return text


def parse_assistant_response(
    raw_text: str,
    max_length: int = DEFAULT_MAX_ASSISTANT_LENGTH,
) -> str:
    """Extract and validate plain-text assistant response from raw LLM output.

    Handles raw plain text, JSON-wrapped objects such as {"response": "..."} or
    {"answer": "..."}, and markdown fenced code blocks. The result must be
    non-empty and no longer than max_length.
    """
    if not raw_text or not raw_text.strip():
        raise AssistantResponseParsingError("Assistant response is empty.")

    text = _strip_code_fences(raw_text.strip())
    text = _unwrap_envelope(_decode_json_like(text), text)
    text = _strip_code_fences(text)
    return _validate_answer(text, max_length)
