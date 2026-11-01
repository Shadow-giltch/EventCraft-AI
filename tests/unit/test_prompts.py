from datetime import date

from eventcraft.domain.personalization import extract_signals
from eventcraft.llm.prompts import (
    OFF_TOPIC_REFUSAL,
    PROMPT_VERSION,
    build_assistant_prompt,
    build_budget_weights_prompt,
    build_ideas_prompt,
)


def test_build_budget_weights_prompt():
    signals = extract_signals(100, date(2026, 8, 1), date(2026, 1, 1), {"style": "Rustic"})
    prompt = build_budget_weights_prompt(["Venue", "Food"], signals)
    assert PROMPT_VERSION in prompt
    assert "Venue" in prompt
    assert "Food" in prompt
    assert "Do NOT invent new category names" in prompt


def test_build_ideas_prompt():
    signals = extract_signals(50, date(2026, 9, 1), date(2026, 1, 1), {"culture": "Global"})
    prompt = build_ideas_prompt("wedding", signals, steer="eco-friendly")
    assert PROMPT_VERSION in prompt
    assert "eco-friendly" in prompt
    assert "5 facets" in prompt


def test_build_assistant_prompt():
    prompt = build_assistant_prompt(
        grounded_summary="Budget: $10,000",
        user_question="When is venue due?",
        chat_history=[("user", "Hello"), ("assistant", "Welcome")],
    )
    assert PROMPT_VERSION in prompt
    assert OFF_TOPIC_REFUSAL in prompt
    assert "Budget: $10,000" in prompt
    assert "When is venue due?" in prompt
