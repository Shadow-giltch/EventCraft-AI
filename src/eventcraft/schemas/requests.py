"""Pydantic v2 request models with strict bounds, extra='forbid', and character checks."""

from datetime import date
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from eventcraft.security.sanitize import has_control_characters

EventTypeLiteral = Literal["wedding", "birthday", "community"]
CurrencyLiteral = Literal["INR", "USD", "EUR", "GBP"]


MAX_LIST_ITEM_CHARS = 50


class EventBriefRequest(BaseModel):
    """Core user inputs specifying requirements for event organization."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    event_type: EventTypeLiteral = Field(..., description="Category of event to organize.")
    event_date: date = Field(..., description="Target date for the celebration.")
    guest_count: int = Field(..., ge=1, le=10000, description="Expected head count.")
    budget_total: Decimal = Field(
        ...,
        gt=Decimal("0.00"),
        le=Decimal("100000000.00"),
        description="Total planned financial budget.",
    )
    currency: CurrencyLiteral = Field(default="INR", description="Three-letter currency code.")
    culture_or_tradition: str = Field(default="", max_length=100)
    style: str = Field(default="", max_length=100)
    priorities: list[str] = Field(default_factory=list, max_length=10)
    dietary_needs: list[str] = Field(default_factory=list, max_length=10)
    accessibility_needs: list[str] = Field(default_factory=list, max_length=10)
    interests: list[str] = Field(default_factory=list, max_length=10)
    steer: str | None = Field(default=None, max_length=300)

    @field_validator("culture_or_tradition", "style", "steer")
    @classmethod
    def validate_no_control_chars(cls, value: str | None) -> str | None:
        """Reject inputs containing harmful control characters."""
        if value and has_control_characters(value):
            raise ValueError("String contains illegal control characters.")
        return value

    @field_validator("priorities", "dietary_needs", "accessibility_needs", "interests")
    @classmethod
    def validate_list_items(cls, items: list[str]) -> list[str]:
        """Validate string elements inside lists for length and control chars."""
        cleaned: list[str] = []
        for item in items:
            trimmed = item.strip()
            if trimmed:
                if len(trimmed) > MAX_LIST_ITEM_CHARS:
                    raise ValueError(f"List item exceeds {MAX_LIST_ITEM_CHARS} character limit.")
                if has_control_characters(trimmed):
                    raise ValueError("List item contains illegal control characters.")
                cleaned.append(trimmed)
        return cleaned


class BudgetRebalanceRequest(BaseModel):
    """Request payload to recalculate budget with zero LLM invocations."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    event_type: EventTypeLiteral
    budget_total: Decimal = Field(..., gt=Decimal("0.00"), le=Decimal("100000000.00"))
    currency: CurrencyLiteral = Field(default="INR")
    guest_count: int = Field(..., ge=1, le=10000)
    priorities: list[str] = Field(default_factory=list, max_length=10)
    custom_weights: dict[str, Decimal] | None = None
    contingency_percent: Decimal = Field(
        default=Decimal("5.00"), ge=Decimal("3.00"), le=Decimal("15.00")
    )


class RegenerateIdeasRequest(BaseModel):
    """Request payload to regenerate only the personalized ideas section."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    brief: EventBriefRequest
    steer: str | None = Field(default=None, max_length=300)

    @field_validator("steer")
    @classmethod
    def validate_steer_chars(cls, value: str | None) -> str | None:
        """Reject steer strings containing control characters."""
        if value and has_control_characters(value):
            raise ValueError("Steer contains illegal control characters.")
        return value



MAX_HISTORY_TEXT_CHARS = 1000
HISTORY_ANSWER_KEYS = ("answer", "response", "assistant", "reply", "content")


def _turn_to_pair(turn: Any) -> Any:
    """Convert a browser chat turn object into a (question, answer) pair."""
    if not isinstance(turn, dict):
        return turn
    question = str(turn.get("question", ""))[:MAX_HISTORY_TEXT_CHARS]
    answer = next((str(turn[key]) for key in HISTORY_ANSWER_KEYS if turn.get(key)), "")
    return (question, answer[:MAX_HISTORY_TEXT_CHARS])



class AssistantAskRequest(BaseModel):
    """Request payload for grounded event planning assistant conversation."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    brief: EventBriefRequest
    question: str = Field(..., min_length=1, max_length=500)
    chat_history: list[tuple[str, str]] = Field(default_factory=list, max_length=6)

    @field_validator("question")
    @classmethod
    def validate_question_clean(cls, value: str) -> str:
        """Reject questions with control characters."""
        if has_control_characters(value):
            raise ValueError("Question contains illegal control characters.")
        return value

    @field_validator("chat_history", mode="before")
    @classmethod
    def accept_turn_objects(cls, value: Any) -> Any:
        """Accept {question, answer} objects from the browser as (question, answer) pairs."""
        if not isinstance(value, list):
            return value
        return [_turn_to_pair(turn) for turn in value]
