"""Pure security utilities for input sanitization and character validation."""

import re
import unicodedata

CONTROL_CHAR_REGEX = re.compile(
    r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f\u200b-\u200f\u202a-\u202e\u2066-\u2069]"
)


def has_control_characters(text: str) -> bool:
    """Check if string contains non-printable control characters or directional overrides."""
    return bool(CONTROL_CHAR_REGEX.search(text))


def sanitize_string(text: str, max_length: int = 500) -> str:
    """Normalize unicode, strip control characters, and truncate safely."""
    if not text:
        return ""
    normalized = unicodedata.normalize("NFKC", text)
    cleaned = CONTROL_CHAR_REGEX.sub("", normalized)
    return cleaned[:max_length].strip()
