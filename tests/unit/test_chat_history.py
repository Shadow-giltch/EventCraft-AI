"""Regression test: browser chat turns are accepted as (question, answer) pairs."""

from eventcraft.schemas.requests import AssistantAskRequest

BRIEF = {
    "event_type": "wedding",
    "event_date": "2027-04-18",
    "guest_count": 100,
    "budget_total": "100000.00",
}


def test_object_style_history_is_converted_to_pairs() -> None:
    """Objects sent by the browser become (question, answer) tuples."""
    request = AssistantAskRequest(
        brief=BRIEF,
        question="Where can I save money?",
        chat_history=[{"question": "hi", "answer": "Hello!"}],
    )
    assert request.chat_history == [("hi", "Hello!")]


def test_long_old_answers_are_trimmed() -> None:
    """An over-long earlier answer is trimmed instead of rejected."""
    request = AssistantAskRequest(
        brief=BRIEF,
        question="Next?",
        chat_history=[{"question": "hi", "answer": "x" * 5000}],
    )
    assert len(request.chat_history[0][1]) <= 1000
