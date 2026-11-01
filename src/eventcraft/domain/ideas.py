"""Pure domain logic for generating personalized event ideas across five facets."""

from dataclasses import dataclass

from eventcraft.domain.personalization import PersonalizationSignals

FACETS = (
    "themes",
    "decor",
    "food & drink",
    "activities/entertainment",
    "keepsakes",
)


@dataclass(frozen=True)
class IdeaItem:
    """Personalized creative recommendation tailored to event brief."""

    facet: str
    title: str
    description: str
    why_it_fits: str
    budget_tier: str  # budget, moderate, premium


@dataclass(frozen=True)
class PersonalizedIdeasPlan:
    """Deliverable containing creative recommendations for all five facets."""

    event_type: str
    steer: str | None
    ideas: list[IdeaItem]


def _build_wedding_fallback(signals: PersonalizationSignals, steer: str | None) -> list[IdeaItem]:
    """Generate personalized wedding ideas matching user signals and steer."""
    culture_label = signals.culture or "your family background"
    style_label = signals.style or "classic elegance"
    steer_suffix = f" with a focus on {steer.strip()}" if steer and steer.strip() else ""

    return [
        IdeaItem(
            facet="themes",
            title=f"Harmonious {style_label.title()} Fusion",
            description=(
                f"A curated celebration celebrating {culture_label}{steer_suffix}, "
                "honoring tradition with contemporary touches."
            ),
            why_it_fits=(
                f"Selected to express your {signals.style or 'preferred'} aesthetic "
                f"while embracing {culture_label}."
            ),
            budget_tier="moderate",
        ),
        IdeaItem(
            facet="decor",
            title="Locally Sourced Seasonal Florals & Ambient Lighting",
            description=(
                "Warm ambient lighting with indigenous botanical table runners and fabric draping."
            ),
            why_it_fits=(
                f"Fits your {signals.guest_size_band} gathering and reflects mindful elegance."
            ),
            budget_tier="moderate",
        ),
        IdeaItem(
            facet="food & drink",
            title="Interactive Regional Tasting Stations",
            description=(
                "Multi-course stations showcasing family heritage dishes and accommodating "
                "special dietary requests."
            ),
            why_it_fits=(
                f"Honors dietary considerations "
                f"({', '.join(signals.dietary_needs) or 'all dietary preferences'}) "
                f"for {signals.guest_size_band} guests."
            ),
            budget_tier="premium"
            if "food" in [p.lower() for p in signals.priorities]
            else "moderate",
        ),
        IdeaItem(
            facet="activities/entertainment",
            title="Acoustic Ceremony & Curated Heritage Playlist",
            description=(
                "Live acoustic ensemble transition to a cultural celebration dance set "
                "welcoming all age groups."
            ),
            why_it_fits=(
                "Designed to engage both seniors and children seamlessly throughout the "
                "celebration."
            ),
            budget_tier="moderate",
        ),
        IdeaItem(
            facet="keepsakes",
            title="Handcrafted Seed Paper Favors & Custom Tea Blends",
            description=(
                "Plantable personalized thank-you cards paired with artisanal regional "
                "tea or spice parcels."
            ),
            why_it_fits=(
                f"Tangible memento echoing {culture_label} hospitality that lasts beyond the event."
            ),
            budget_tier="budget",
        ),
    ]


def _build_birthday_fallback(signals: PersonalizationSignals, steer: str | None) -> list[IdeaItem]:
    """Generate personalized birthday ideas matching age group and signals."""
    interests_str = ", ".join(signals.interests) or "shared favorite passions"
    steer_suffix = f" featuring {steer.strip()}" if steer and steer.strip() else ""

    return [
        IdeaItem(
            facet="themes",
            title=f"Signature Celebration: {signals.style or 'Festive'} Spotlight",
            description=f"A vibrant party centered around {interests_str}{steer_suffix}.",
            why_it_fits=f"Personalized to highlight interests in {interests_str}.",
            budget_tier="moderate",
        ),
        IdeaItem(
            facet="decor",
            title="Color-Blocked Photo Backdrop & Custom Banners",
            description=(
                "A bold balloon or fabric garland accent wall with milestone photo moments."
            ),
            why_it_fits=(
                f"Scales effectively for a {signals.guest_size_band} guest party without clutter."
            ),
            budget_tier="budget",
        ),
        IdeaItem(
            facet="food & drink",
            title="Signature Slider & Mocktail/Cocktail Bar",
            description=(
                "Build-your-own artisan bite station paired with personalized signature "
                "event refreshments."
            ),
            why_it_fits=(
                "Provides flexible options accommodating "
                f"{signals.dietary_needs or 'varied guest palates'}."
            ),
            budget_tier="moderate",
        ),
        IdeaItem(
            facet="activities/entertainment",
            title="Interactive Trivia & Memory Time-Capsule",
            description=(
                "Custom group trivia about the honoree followed by an open-mic milestone toast."
            ),
            why_it_fits="High-energy connection tailored to engage your guest group.",
            budget_tier="budget",
        ),
        IdeaItem(
            facet="keepsakes",
            title="Custom Polaroids & Mini Treat Packages",
            description=(
                "Instant photo magnet frames and gourmet confectionery boxes personalized "
                "for attendees."
            ),
            why_it_fits="Memorable, instant take-home gift suited to your guest count.",
            budget_tier="budget",
        ),
    ]


def _build_community_fallback(signals: PersonalizationSignals, steer: str | None) -> list[IdeaItem]:
    """Generate personalized community event ideas matching neighborhood signals."""
    steer_suffix = f" highlighting {steer.strip()}" if steer and steer.strip() else ""

    return [
        IdeaItem(
            facet="themes",
            title=f"Neighbors United: {signals.style or 'Open'} Gathering",
            description=(
                "An inclusive neighborhood initiative bringing diverse residents together"
                f"{steer_suffix}."
            ),
            why_it_fits=f"Designed for your {signals.guest_size_band} community turnout.",
            budget_tier="budget",
        ),
        IdeaItem(
            facet="decor",
            title="Recyclable Wayfinding & Community Art Murals",
            description=(
                "High-visibility bilingual signage boards and a collaborative community "
                "chalkboard wall."
            ),
            why_it_fits="Prioritizes accessible navigation and community contribution.",
            budget_tier="budget",
        ),
        IdeaItem(
            facet="food & drink",
            title="Local Bakeries & Refreshment Hydration Hub",
            description=(
                "Community potluck or local business-sponsored snack tables with compostable cups."
            ),
            why_it_fits="Supports neighborhood economy and broad dietary accessibility.",
            budget_tier="budget",
        ),
        IdeaItem(
            facet="activities/entertainment",
            title="Multi-Generational Workshop & Acoustic Showcase",
            description=(
                "Hands-on community learning stations paired with an open-mic stage for "
                "local talent."
            ),
            why_it_fits=(
                "Inclusive activities ensuring both youth and seniors actively participate."
            ),
            budget_tier="budget",
        ),
        IdeaItem(
            facet="keepsakes",
            title="Community Seed Packets & Printed Resource Guide",
            description=(
                "Native plant seed packets with a directory of local neighborhood initiatives."
            ),
            why_it_fits="Long-term positive community impact extending past event day.",
            budget_tier="budget",
        ),
    ]


def build_deterministic_ideas(
    event_type: str,
    signals: PersonalizationSignals,
    steer: str | None = None,
) -> PersonalizedIdeasPlan:
    """Generate five-facet personalized ideas using deterministic rule engine."""
    clean_type = event_type.strip().lower()
    if "wedding" in clean_type:
        ideas = _build_wedding_fallback(signals, steer)
    elif "birthday" in clean_type:
        ideas = _build_birthday_fallback(signals, steer)
    else:
        ideas = _build_community_fallback(signals, steer)

    return PersonalizedIdeasPlan(
        event_type=event_type,
        steer=steer,
        ideas=ideas,
    )
