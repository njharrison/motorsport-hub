"""F1CalendarSource — Formula 3 source using the f1calendar open-source dataset.

Delegates all HTTP, cache, and mapping logic to F1CalendarBaseSource.
Only F3-specific configuration (session map, circuit data, championship) lives here.

Source: https://github.com/sportstimes/f1 (MIT license).
URL: https://raw.githubusercontent.com/sportstimes/f1/main/_db/f3/{year}.json

Session format note: the f1calendar dataset uses key "practice" (not "fp1") for
the F3 free-practice session, and "sprint" (not "sprintRace") for the sprint race.
This differs from the F2 session keys. Seasons prior to 2022 used "race1"/"race2"/"race3"
and are not mapped by this source — those sessions will be silently skipped.
"""

from __future__ import annotations

from motorsport_calendar.models import Championship, ChampionshipCategory, SessionType
from motorsport_calendar.providers.formula3.source import Formula3Source
from motorsport_calendar.providers.support_series.f1calendar_base import F1CalendarBaseSource

__all__ = ["F1CalendarSource"]

# F3-specific: session key → (SessionType, duration minutes, display title)
# Keys confirmed from f1calendar dataset 2022-2025.
_SESSION_MAP: dict[str, tuple[SessionType, int, str]] = {
    "practice": (SessionType.FP1, 45, "Free Practice"),
    "qualifying": (SessionType.QUALIFYING, 30, "Qualifying"),
    "sprint": (SessionType.SPRINT, 30, "Sprint Race"),
    "feature": (SessionType.RACE, 40, "Feature Race"),
}

# F3 circuit slug (f1calendar localeKey) → (country, IANA timezone)
# Covers all slugs observed in f1calendar dataset 2021-2025.
_CIRCUIT_DATA: dict[str, tuple[str, str]] = {
    "bahrain": ("Bahrain", "Asia/Bahrain"),
    "melbourne": ("Australia", "Australia/Melbourne"),
    "emilia-romagna": ("Italy", "Europe/Rome"),
    "monaco": ("Monaco", "Europe/Monaco"),
    "spanish": ("Spain", "Europe/Madrid"),
    "austrian": ("Austria", "Europe/Vienna"),
    "british": ("UK", "Europe/London"),
    "hungarian": ("Hungary", "Europe/Budapest"),
    "belgian": ("Belgium", "Europe/Brussels"),
    "italian": ("Italy", "Europe/Rome"),
    "dutch": ("Netherlands", "Europe/Amsterdam"),
    "french": ("France", "Europe/Paris"),
    "russian": ("Russia", "Europe/Moscow"),
}


class F1CalendarSource(F1CalendarBaseSource, Formula3Source):
    """Formula 3 source backed by the f1calendar open dataset.

    Inherits all HTTP, cache, and mapping logic from F1CalendarBaseSource.
    The four properties below are the only F3-specific configuration.
    """

    @property
    def _series_key(self) -> str:
        return "f3"

    @property
    def _session_map(self) -> dict[str, tuple[SessionType, int, str]]:
        return _SESSION_MAP

    @property
    def _circuit_data(self) -> dict[str, tuple[str, str]]:
        return _CIRCUIT_DATA

    def _make_championship(self, year: int) -> Championship:
        return Championship(
            id=f"formula3-{year}",
            name="FIA Formula 3 Championship",
            category=ChampionshipCategory.SINGLE_SEATER,
        )
