"""Gap-closing tests for eventcraft.domain.ideas (deterministic fallback engine)."""

from types import SimpleNamespace

import pytest

from eventcraft.domain.ideas import FACETS, build_deterministic_ideas


def signals(**kw):
    base = dict(
        culture=None,
        style=None,
        priorities=[],
        dietary_needs=[],
        interests=[],
        guest_size_band="medium",
    )
    base.update(kw)
    return SimpleNamespace(**base)


@pytest.mark.parametrize("event_type", ["wedding", "birthday", "community", "Corporate Gala"])
def test_every_event_type_returns_all_five_facets_once(event_type):
    plan = build_deterministic_ideas(event_type, signals())
    assert [i.facet for i in plan.ideas] == list(FACETS)
    assert all(i.title and i.description and i.why_it_fits for i in plan.ideas)
    assert all(i.budget_tier in {"budget", "moderate", "premium"} for i in plan.ideas)


@pytest.mark.parametrize("raw", ["  WEDDING ", "Birthday Party", "Big Fat Wedding Reception"])
def test_event_type_is_matched_case_insensitively_by_substring(raw):
    plan = build_deterministic_ideas(raw, signals())
    assert plan.event_type == raw  # original preserved
    assert len(plan.ideas) == 5


def test_unknown_event_type_uses_community_fallback():
    assert [i.title for i in build_deterministic_ideas("rave", signals()).ideas] == [
        i.title for i in build_deterministic_ideas("community", signals()).ideas
    ]


@pytest.mark.parametrize("event_type", ["wedding", "birthday", "community"])
def test_steer_is_woven_in_when_present_and_blank_steer_is_ignored(event_type):
    with_steer = build_deterministic_ideas(event_type, signals(), steer="vintage jazz")
    blank = build_deterministic_ideas(event_type, signals(), steer="   ")
    none = build_deterministic_ideas(event_type, signals(), steer=None)
    assert with_steer.steer == "vintage jazz"
    assert "vintage jazz" in " ".join(i.description + i.title for i in with_steer.ideas)
    assert [i.description for i in blank.ideas] == [i.description for i in none.ideas]


def test_wedding_uses_culture_or_default_label():
    named = build_deterministic_ideas("wedding", signals(culture="Rajasthani"))
    unnamed = build_deterministic_ideas("wedding", signals())
    assert "Rajasthani" in " ".join(i.description + i.why_it_fits for i in named.ideas)
    assert "your family background" in " ".join(i.description + i.why_it_fits for i in unnamed.ideas)


def test_wedding_food_priority_upgrades_budget_tier():
    food = build_deterministic_ideas("wedding", signals(priorities=["Food"]))
    plain = build_deterministic_ideas("wedding", signals())
    tier = lambda p: next(i for i in p.ideas if i.facet == "food & drink").budget_tier  # noqa: E731
    assert tier(food) == "premium"
    assert tier(plain) == "moderate"


def test_birthday_interests_fallback_phrase_when_empty():
    plain = build_deterministic_ideas("birthday", signals())
    rich = build_deterministic_ideas("birthday", signals(interests=["chess", "anime"]))
    assert "shared favorite passions" in " ".join(i.description for i in plain.ideas)
    assert "chess, anime" in " ".join(i.description for i in rich.ideas)
