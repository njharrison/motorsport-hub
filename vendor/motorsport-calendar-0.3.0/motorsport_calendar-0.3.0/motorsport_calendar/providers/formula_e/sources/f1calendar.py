"""F1CalendarSource — Formula E source using the f1calendar open-source dataset.

Delegates all HTTP, cache, and mapping logic to F1CalendarBaseSource.
Only Formula E-specific configuration (session map, circuit data, championship)
lives here.

Source: https://github.com/sportstimes/f1 (MIT license).
URL: https://raw.githubusercontent.com/sportstimes/f1/main/_db/fe/{year}.json

Session format (confirmed from dataset 2023-2025):
    practice1  → Free Practice 1
    practice2  → Free Practice 2
    practice3  → Free Practice 3 (only on the second day of a double-header
                 round — replaces practice1/practice2 for that round)
    qualifying → Qualifying (group stages + duels)
    race       → Race

Unlike F1 Academy's triple-header (one Event with race1/race2/race3), Formula E
splits each double-header day into its own round/Event with a single "race"
session — no SessionType collision, no UID workaround needed. Some rounds omit
qualifying or a practice session entirely (e.g. Tokyo round 8 in 2025 has no
qualifying); the shared `_build_event` loop already skips absent keys.

Coverage: 2023 → present. Seasons prior to 2023 are not available in the dataset.
"""

from __future__ import annotations

from motorsport_calendar.models import Championship, ChampionshipCategory, SessionType
from motorsport_calendar.providers.formula_e.source import FormulaESource
from motorsport_calendar.providers.support_series.f1calendar_base import F1CalendarBaseSource

__all__ = ["F1CalendarSource"]

# Formula E-specific: session key → (SessionType, duration minutes, display title)
# Keys confirmed from f1calendar dataset 2023-2025.
_SESSION_MAP: dict[str, tuple[SessionType, int, str]] = {
    "practice1": (SessionType.FP1, 30, "Free Practice 1"),
    "practice2": (SessionType.FP2, 30, "Free Practice 2"),
    "practice3": (SessionType.FP3, 30, "Free Practice 3"),
    "qualifying": (SessionType.QUALIFYING, 60, "Qualifying"),
    "race": (SessionType.RACE, 45, "Race"),
}

# Formula E circuit slug (f1calendar localeKey) → (country, IANA timezone)
# Covers all slugs observed in f1calendar dataset 2023-2025.
_CIRCUIT_DATA: dict[str, tuple[str, str]] = {
    "sao-paulo-eprix": ("Brazil", "America/Sao_Paulo"),
    "mexico-city-eprix": ("Mexico", "America/Mexico_City"),
    "jeddah-eprix": ("Saudi Arabia", "Asia/Riyadh"),
    "diriyah-eprix": ("Saudi Arabia", "Asia/Riyadh"),
    "miami-eprix": ("USA", "America/New_York"),
    "monaco-eprix": ("Monaco", "Europe/Monaco"),
    "tokyo-eprix": ("Japan", "Asia/Tokyo"),
    "shanghai-eprix": ("China", "Asia/Shanghai"),
    "jakarta-eprix": ("Indonesia", "Asia/Jakarta"),
    "berlin-eprix": ("Germany", "Europe/Berlin"),
    "london-eprix": ("United Kingdom", "Europe/London"),
    "misano-eprix": ("Italy", "Europe/Rome"),
    "rome-eprix": ("Italy", "Europe/Rome"),
    "portland-eprix": ("USA", "America/Los_Angeles"),
    "hyderabad-eprix": ("India", "Asia/Kolkata"),
    "cape-town-eprix": ("South Africa", "Africa/Johannesburg"),
}


class F1CalendarSource(F1CalendarBaseSource, FormulaESource):
    """Formula E source backed by the f1calendar open dataset.

    Inherits all HTTP, cache, and mapping logic from F1CalendarBaseSource.
    The four properties below are the only Formula E-specific configuration.
    """

    @property
    def _series_key(self) -> str:
        return "fe"

    @property
    def _session_map(self) -> dict[str, tuple[SessionType, int, str]]:
        return _SESSION_MAP

    @property
    def _circuit_data(self) -> dict[str, tuple[str, str]]:
        return _CIRCUIT_DATA

    def _make_championship(self, year: int) -> Championship:
        return Championship(
            id=f"formula-e-{year}",
            name="Formula E",
            category=ChampionshipCategory.SINGLE_SEATER,
        )
