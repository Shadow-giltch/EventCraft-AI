"""Knowledge base loader validating event type JSON templates at startup."""

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from eventcraft.domain.budget import CategoryConfig
from eventcraft.domain.timeline import MilestoneTemplate, RunOfShowItem
from eventcraft.domain.vendors import VendorItemTemplate

CURRENT_DIR = Path(__file__).resolve().parent


@dataclass(frozen=True)
class EventKnowledgeBase:
    """Validated domain models extracted from knowledge base JSON files."""

    event_type: str
    budget_categories: list[CategoryConfig]
    milestones: list[MilestoneTemplate]
    run_of_show: list[RunOfShowItem]
    vendor_categories: list[VendorItemTemplate]


def _parse_budget_categories(raw_list: list[dict[str, object]]) -> list[CategoryConfig]:
    """Parse and validate budget category templates."""
    categories: list[CategoryConfig] = []
    for item in raw_list:
        categories.append(
            CategoryConfig(
                name=str(item["name"]),
                default_percent=Decimal(str(item["default_percent"])),
                min_percent=Decimal(str(item["min_percent"])),
                max_percent=Decimal(str(item["max_percent"])),
                rationale=str(item["rationale"]),
                saving_tip=str(item["saving_tip"]),
            )
        )
    return categories


def _parse_milestones(raw_list: list[dict[str, object]]) -> list[MilestoneTemplate]:
    """Parse and validate milestone schedule templates."""
    milestones: list[MilestoneTemplate] = []
    for item in raw_list:
        raw_deps = item.get("depends_on")
        deps = (
            [str(d) for d in raw_deps]
            if isinstance(raw_deps, Sequence) and not isinstance(raw_deps, (str, bytes))
            else []
        )
        milestones.append(
            MilestoneTemplate(
                id=str(item["id"]),
                title=str(item["title"]),
                phase=str(item["phase"]),
                lead_days=int(str(item["lead_days"])),
                priority=str(item["priority"]),
                depends_on=deps,
                notes=str(item.get("notes", "")),
            )
        )
    return milestones


def _parse_run_of_show(raw_list: list[dict[str, object]]) -> list[RunOfShowItem]:
    """Parse and validate run-of-show schedule items."""
    items: list[RunOfShowItem] = []
    for item in raw_list:
        items.append(
            RunOfShowItem(
                time=str(item["time"]),
                activity=str(item["activity"]),
                responsible=str(item["responsible"]),
                notes=str(item.get("notes", "")),
            )
        )
    return items


def _parse_vendors(raw_list: list[dict[str, object]]) -> list[VendorItemTemplate]:
    """Parse and validate vendor vetting category templates."""
    vendors: list[VendorItemTemplate] = []
    for item in raw_list:
        raw_q = item.get("questions_to_ask")
        raw_d = item.get("documents_to_verify")
        raw_r = item.get("red_flags")
        q_list = (
            [str(q) for q in raw_q]
            if isinstance(raw_q, Sequence) and not isinstance(raw_q, (str, bytes))
            else []
        )
        d_list = (
            [str(d) for d in raw_d]
            if isinstance(raw_d, Sequence) and not isinstance(raw_d, (str, bytes))
            else []
        )
        r_list = (
            [str(r) for r in raw_r]
            if isinstance(raw_r, Sequence) and not isinstance(raw_r, (str, bytes))
            else []
        )
        vendors.append(
            VendorItemTemplate(
                id=str(item["id"]),
                category=str(item["category"]),
                title=str(item["title"]),
                budget_line=str(item["budget_line"]),
                milestone_id=str(item["milestone_id"]),
                questions_to_ask=q_list,
                documents_to_verify=d_list,
                red_flags=r_list,
            )
        )
    return vendors


def load_knowledge_template(file_path: Path) -> EventKnowledgeBase:
    """Load and validate a single knowledge base JSON file."""
    with file_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    event_type = str(data["event_type"])
    budget_cats = _parse_budget_categories(data.get("budget_categories", []))
    milestones = _parse_milestones(data.get("milestones", []))
    run_of_show = _parse_run_of_show(data.get("run_of_show", []))
    vendors = _parse_vendors(data.get("vendor_categories", []))

    return EventKnowledgeBase(
        event_type=event_type,
        budget_categories=budget_cats,
        milestones=milestones,
        run_of_show=run_of_show,
        vendor_categories=vendors,
    )


class KnowledgeRepository:
    """In-memory registry of validated event knowledge templates."""

    def __init__(self, templates: Mapping[str, EventKnowledgeBase]) -> None:
        """Initialize repository with loaded templates."""
        self._templates = dict(templates)

    @classmethod
    def load_from_directory(cls, dir_path: Path = CURRENT_DIR) -> "KnowledgeRepository":
        """Scan directory and validate all event knowledge JSON templates."""
        templates: dict[str, EventKnowledgeBase] = {}
        for target in ["wedding", "birthday", "community"]:
            target_path = dir_path / f"{target}.json"
            if not target_path.exists():
                raise FileNotFoundError(f"Missing required knowledge template: {target_path}")
            loaded = load_knowledge_template(target_path)
            templates[target] = loaded

        return cls(templates)

    def get(self, event_type: str) -> EventKnowledgeBase:
        """Retrieve knowledge base matching event type, falling back cleanly."""
        clean = event_type.strip().lower()
        if "wedding" in clean:
            return self._templates["wedding"]
        if "birthday" in clean:
            return self._templates["birthday"]
        return self._templates["community"]
