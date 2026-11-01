"""Deterministic offline template engine implementing LLMClient without network calls."""

import json
import time

from eventcraft.domain.ideas import FACETS
from eventcraft.llm.base import LLMResponse


class OfflineClient:
    """Fallback template engine providing valid structured JSON responses offline."""

    async def generate(
        self,
        prompt: str,
        temperature: float = 0.2,
        max_output_tokens: int = 1024,
    ) -> LLMResponse:
        """Produce deterministic, schema-compliant JSON response without network."""
        start_time = time.monotonic()

        if "weights" in prompt.lower() and "budget" in prompt.lower():
            # Standard balanced weights template
            data = {
                "weights": {
                    "Venue & Rentals": 30.0,
                    "Catering & Bar": 28.0,
                    "Photography & Video": 12.0,
                    "Decor & Florals": 10.0,
                    "Music & Entertainment": 7.0,
                }
            }
            content = json.dumps(data)
        elif "activities/entertainment" in prompt or "keepsakes" in prompt:
            # Deterministic five-facet ideas
            ideas_list = [
                {
                    "facet": facet,
                    "title": f"Curated {facet.title()} Concept",
                    "description": (
                        f"Tailored {facet} recommendation balanced for your event scale."
                    ),
                    "why_it_fits": "Derived from your provided guest size and planning priorities.",
                    "budget_tier": "moderate",
                }
                for facet in FACETS
            ]
            content = json.dumps({"ideas": ideas_list})
        else:
            # Assistant query response
            content = (
                "Based on your event plan, all timeline milestones and budget allocations "
                "have been calculated according to your target date and guest size."
            )

        elapsed_ms = int((time.monotonic() - start_time) * 1000)
        return LLMResponse(
            content=content,
            source="template",
            latency_ms=max(1, elapsed_ms),
            tokens_used=None,
        )
