"""F1CalendarSource — F1 Academy source using the f1calendar open-source dataset.

Delegates all HTTP, cache, and mapping logic to F1CalendarBaseSource.
Only F1 Academy-specific configuration (session map, circuit data, championship) lives here.

Source: https://github.com/sportstimes/f1 (MIT license).
URL: https://raw.githubusercontent.com/sportstimes/f1/main/_db/f1-academy/{year}.json

Session format (confirmed from dataset 2023-2025):
    fp1         → Free Practice 1
    fp2         → Free Practice 2
    qualifying1 → Qualifying 1 (grid for Race 1 / main race)
    qualifying2 → Qualifying 2 (only in 2023-2024 seasons)
    race1       → Race 1 (sprint-length, ~30 min)
    race2       → Race 2 (sprint-length, ~30 min)
    race3       → Race 3 (main race, ~30 min)

SessionType mapping constraint: F1 Academy's three-race format requires three distinct
SessionType values to avoid colliding ICS UIDs (RFC 5545). No SessionType enum change
is required thanks to the following mapping:
    race1 → SPRINT        (sprint = short standalone race ✓)
    race2 → FP3           (workaround — FP3 ensures unique UID; title shown is "Race 2")
    race3 → RACE          (main/feature race ✓)
See ADR-016 for the rationale and the recommendation to add RACE2/RACE3 to SessionType.

Coverage: 2023 → present. Seasons prior to 2023 are not available in the dataset.
"""

from __future__ import annotations

from motorsport_calendar.models import Championship, ChampionshipCategory, SessionType
from motorsport_calendar.providers.f1_academy.source import F1AcademySource
from motorsport_calendar.providers.support_series.f1calendar_base import F1CalendarBaseSource

__all__ = ["F1CalendarSource"]

# F1 Academy-specific: session key → (SessionType, duration minutes, display title)
# Keys confirmed from f1calendar dataset 2023-2025.
_SESSION_MAP: dict[str, tuple[SessionType, int, str]] = {
    "fp1": (SessionType.FP1, 45, "Free Practice 1"),
    "fp2": (SessionType.FP2, 30, "Free Practice 2"),
    "qualifying1": (SessionType.QUALIFYING, 30, "Qualifying 1"),
    # qualifying2 only present in 2023-2024 seasons.
    "qualifying2": (SessionType.SPRINT_QUALIFYING, 30, "Qualifying 2"),
    # Three races map to SPRINT/FP3/RACE to guarantee unique ICS UIDs without model changes.
    "race1": (SessionType.SPRINT, 30, "Race 1"),
    "race2": (SessionType.FP3, 30, "Race 2"),  # see module docstring
    "race3": (SessionType.RACE, 30, "Race 3"),
}

# F1 Academy circuit slug (f1calendar localeKey) → (country, IANA timezone)
# Covers all slugs observed in f1calendar dataset 2023-2025.
# Note: "valenvia" is the actual slug in the dataset (typo for Valencia in 2023).
_CIRCUIT_DATA: dict[str, tuple[str, str]] = {
    "chinese": ("China", "Asia/Shanghai"),
    "jeddah": ("Saudi Arabia", "Asia/Riyadh"),
    "miami": ("USA", "America/New_York"),
    "canadian": ("Canada", "America/Toronto"),
    "zandvoort": ("Netherlands", "Europe/Amsterdam"),
    "singapore": ("Singapore", "Asia/Singapore"),
    "las-vegas": ("USA", "America/Los_Angeles"),
    "barcelona": ("Spain", "Europe/Madrid"),
    "qatar": ("Qatar", "Asia/Qatar"),
    "abu-dhabi": ("UAE", "Asia/Dubai"),
    "spielberg": ("Austria", "Europe/Vienna"),
    "valenvia": ("Spain", "Europe/Madrid"),
    "monza": ("Italy", "Europe/Rome"),
    "la-castellet": ("France", "Europe/Paris"),
    "austin": ("USA", "America/Chicago"),
}


class F1CalendarSource(F1CalendarBaseSource, F1AcademySource):
    """F1 Academy source backed by the f1calendar open dataset.

    Inherits all HTTP, cache, and mapping logic from F1CalendarBaseSource.
    The four properties below are the only F1 Academy-specific configuration.
    """

    @property
    def _series_key(self) -> str:
        return "f1-academy"

    @property
    def _session_map(self) -> dict[str, tuple[SessionType, int, str]]:
        return _SESSION_MAP

    @property
    def _circuit_data(self) -> dict[str, tuple[str, str]]:
        return _CIRCUIT_DATA

    def _make_championship(self, year: int) -> Championship:
        return Championship(
            id=f"f1-academy-{year}",
            name="F1 Academy",
            category=ChampionshipCategory.SINGLE_SEATER,
        )
