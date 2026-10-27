"""Championship category groups for visual grouping in the GUI.

Architecture:
  Category   — enum of all possible disciplines (present and future)
  ChampionshipGroup — ordered group of IDs belonging to one category
  GROUPS     — registry consumed by the view

To add a new group (e.g. Moto):
  1. Add MOTO = "moto" to Category (if not already present)
  2. Append a ChampionshipGroup entry to GROUPS
  3. Create the provider/source in motorsport_calendar/providers/
  No other GUI changes needed.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Category(StrEnum):
    """High-level motorsport disciplines — present and future."""

    FORMULA = "formula"
    ENDURANCE = "endurance"
    GT = "gt"
    MOTO = "moto"
    RALLY = "rally"
    AMERICA = "america"


@dataclass(frozen=True)
class ChampionshipGroup:
    """A labelled group of championships displayed together in the UI."""

    category: Category
    label: str  # e.g. "Formula"
    emoji: str  # e.g. "🏎"
    championship_ids: tuple[str, ...]  # display order within the group


# Ordered list of groups displayed in the championship section.
# Only IDs actually present in ProviderRegistry will appear — the rest are silently ignored.
GROUPS: list[ChampionshipGroup] = [
    ChampionshipGroup(
        category=Category.FORMULA,
        label="Formula",
        emoji="🏎",
        championship_ids=("formula1", "formula2", "formula3", "f1-academy", "formula-e"),
    ),
    ChampionshipGroup(
        category=Category.ENDURANCE,
        label="Endurance",
        emoji="🏁",
        championship_ids=("wec", "elms", "mlmc", "imsa"),
    ),
    ChampionshipGroup(
        category=Category.GT,
        label="GT",
        emoji="🚗",
        championship_ids=("gtwc-europe", "gtwc-america", "gtwc-asia", "igtc"),
    ),
    ChampionshipGroup(
        category=Category.MOTO,
        label="Moto",
        emoji="🏍",
        championship_ids=("motogp", "moto2", "moto3", "worldsbk"),
    ),
]


def get_groups_for(available_ids: list[str]) -> list[tuple[ChampionshipGroup, list[str]]]:
    """Return (group, ids_in_group) pairs for groups that have available championships.

    Championship IDs present in *available_ids* but not listed in any GROUPS entry
    are collected into an implicit fallback group so they always surface in the UI.
    """
    result: list[tuple[ChampionshipGroup, list[str]]] = []
    used: set[str] = set()

    for group in GROUPS:
        ids = [cid for cid in group.championship_ids if cid in available_ids]
        if ids:
            result.append((group, ids))
            used.update(ids)

    ungrouped = [cid for cid in available_ids if cid not in used]
    if ungrouped:
        fallback = ChampionshipGroup(
            category=Category.FORMULA,
            label="Autres",
            emoji="🏆",
            championship_ids=tuple(ungrouped),
        )
        result.append((fallback, ungrouped))

    return result
