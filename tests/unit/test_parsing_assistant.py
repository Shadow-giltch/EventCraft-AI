"""Tests for assistant-response parsing and JSON repair."""

import json

import pytest

from eventcraft.llm.parsing import (
    AssistantResponseParsingError,
    JSONRepairFailedError,
    parse_and_repair_json,
    parse_assistant_response,
)

FENCE = "`" * 3


def test_plain_text_is_returned_unchanged() -> None:
    """Plain text passes through."""
    assert parse_assistant_response("Hello there") == "Hello there"


@pytest.mark.parametrize("key", ["response", "answer", "text"])
def test_json_envelope_keys_are_unwrapped(key: str) -> None:
    """Supported envelope keys give back only the answer text."""
    assert parse_assistant_response(json.dumps({key: " Hi! "})) == "Hi!"


def test_fenced_json_envelope_is_unwrapped() -> None:
    """A fenced JSON envelope is stripped and unwrapped."""
    raw = f'{FENCE}json\n{{"response": "Hi"}}\n{FENCE}'
    assert parse_assistant_response(raw) == "Hi"


def test_quoted_json_string_is_unwrapped() -> None:
    """A JSON string literal returns its inner text."""
    assert parse_assistant_response('"Just text"') == "Just text"


def test_trailing_comma_envelope_is_repaired() -> None:
    """One repair attempt fixes a trailing comma."""
    assert parse_assistant_response('{"response": "Hi",}') == "Hi"


def test_undecodable_object_text_is_returned_as_is() -> None:
    """Unrepairable JSON-looking text falls back to the raw text."""
    assert parse_assistant_response("{not json}") == "{not json}"


def test_nested_fence_inside_answer_is_stripped() -> None:
    """A fenced answer inside the envelope is cleaned."""
    raw = json.dumps({"response": f"{FENCE}\nInner\n{FENCE}"})
    assert parse_assistant_response(raw) == "Inner"


@pytest.mark.parametrize("raw", ['{"other": "x"}', '{"response": 5}'])
def test_envelope_without_text_key_is_rejected(raw: str) -> None:
    """An envelope with no usable string key raises."""
    with pytest.raises(AssistantResponseParsingError):
        parse_assistant_response(raw)


@pytest.mark.parametrize("raw", ["", "   ", '{"response": "   "}'])
def test_empty_answers_are_rejected(raw: str) -> None:
    """Empty input or an empty unwrapped answer raises."""
    with pytest.raises(AssistantResponseParsingError):
        parse_assistant_response(raw)


def test_over_long_answer_is_rejected() -> None:
    """An answer above the cap raises."""
    with pytest.raises(AssistantResponseParsingError):
        parse_assistant_response("a" * 20, max_length=10)


def test_valid_json_object_is_parsed() -> None:
    """A valid object parses without repair."""
    assert parse_and_repair_json('{"a": 1}') == {"a": 1}


def test_fenced_trailing_comma_json_is_repaired() -> None:
    """Fences and a trailing comma are fixed in one repair."""
    assert parse_and_repair_json(f'{FENCE}json\n{{"a": 1,}}\n{FENCE}') == {"a": 1}


def test_json_surrounded_by_prose_is_extracted() -> None:
    """The outermost object is extracted from surrounding text."""
    assert parse_and_repair_json('Here: {"a": 1} thanks') == {"a": 1}


@pytest.mark.parametrize("raw", ["", "not json at all", "[1]"])
def test_unrepairable_json_raises(raw: str) -> None:
    """Empty, non-JSON and non-object roots raise a repair error."""
    with pytest.raises(JSONRepairFailedError):
        parse_and_repair_json(raw)
