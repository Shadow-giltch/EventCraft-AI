from datetime import date

from eventcraft.domain.personalization import (
    derive_guest_band,
    derive_lead_band,
    extract_signals,
)


def test_derive_bands():
    assert derive_guest_band(25) == "intimate"
    assert derive_guest_band(80) == "medium"
    assert derive_guest_band(200) == "large"
    assert derive_guest_band(500) == "mega"

    assert derive_lead_band(15) == "urgent"
    assert derive_lead_band(60) == "moderate"
    assert derive_lead_band(180) == "relaxed"


def test_extract_signals_cleans_inputs():
    today = date(2026, 1, 1)
    event_date = date(2026, 6, 1)
    ctx = {
        "children_present": True,
        "seniors_present": False,
        "priorities": [" Photography ", "Music"],
        "dietary_needs": [" Vegan ", ""],
        "culture": " South Indian ",
        "style": " Modern Minimalist ",
    }
    signals = extract_signals(120, event_date, today, ctx)

    assert signals.guest_size_band == "large"
    assert signals.lead_time_band == "relaxed"
    assert signals.children_present is True
    assert signals.priorities == ["Photography", "Music"]
    assert signals.dietary_needs == ["Vegan"]
    assert signals.culture == "South Indian"
    assert signals.style == "Modern Minimalist"
