"""Edge-case tests for request validation and fenced-text parsing."""

import pytest
from pydantic import ValidationError

from eventcraft.llm.parsing import parse_assistant_response
from eventcraft.schemas.requests import AssistantAskRequest, EventBriefRequest

FENCE = "`" * 3
BRIEF = {
    "event_type": "wedding",
    "event_date": "2027-04-18",
    "guest_count": 100,
    "budget_total": "100000.00",
}


def test_fence_without_closing_marker_keeps_the_text() -> None:
    """An opening fence with no closing fence still yields the answer text."""
    assert parse_assistant_response(f"{FENCE}text\nplain answer") == "plain answer"


def test_pair_shaped_history_turns_pass_through() -> None:
    """History already in (question, answer) form is accepted unchanged."""
    request = AssistantAskRequest(brief=BRIEF, question="Next?", chat_history=[("hi", "Hello!")])
    assert request.chat_history == [("hi", "Hello!")]


def test_non_list_history_is_rejected() -> None:
    """A history that is not a list fails validation."""
    with pytest.raises(ValidationError):
        AssistantAskRequest(brief=BRIEF, question="Next?", chat_history="oops")


def test_blank_list_items_are_dropped() -> None:
    """Whitespace-only entries in list fields are removed."""
    brief = EventBriefRequest(**BRIEF, priorities=["  ", "catering"])
    assert brief.priorities == ["catering"]
