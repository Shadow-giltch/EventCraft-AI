from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from eventcraft.schemas.requests import (
    AssistantAskRequest,
    EventBriefRequest,
    RegenerateIdeasRequest,
)


def test_request_list_item_too_long_raises():
    with pytest.raises(ValidationError, match="exceeds 50 character limit"):
        EventBriefRequest(
            event_type="wedding",
            event_date=date(2027, 1, 1),
            guest_count=100,
            budget_total=Decimal("1000.00"),
            priorities=["A" * 60],
        )


def test_request_list_item_control_chars_raises():
    with pytest.raises(ValidationError, match="illegal control characters"):
        EventBriefRequest(
            event_type="wedding",
            event_date=date(2027, 1, 1),
            guest_count=100,
            budget_total=Decimal("1000.00"),
            priorities=["Bad\x00Priority"],
        )


def test_regenerate_ideas_steer_control_chars_raises():
    brief = EventBriefRequest(
        event_type="birthday",
        event_date=date(2027, 1, 1),
        guest_count=20,
        budget_total=Decimal("500.00"),
    )
    with pytest.raises(ValidationError, match="illegal control characters"):
        RegenerateIdeasRequest(brief=brief, steer="Bad\x00Steer")


def test_assistant_question_control_chars_raises():
    brief = EventBriefRequest(
        event_type="birthday",
        event_date=date(2027, 1, 1),
        guest_count=20,
        budget_total=Decimal("500.00"),
    )
    with pytest.raises(ValidationError, match="illegal control characters"):
        AssistantAskRequest(brief=brief, question="Question\x00here")
