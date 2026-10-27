"""F1CalendarSource — Formula 2 source using the f1calendar open-source dataset.

Delegates all HTTP, cache, and mapping logic to F1CalendarBaseSource.
Only F2-specific configuration (session map, circuit data, championship) lives here.

Source: https://github.com/sportstimes/f1 (MIT license).
URL: https://raw.githubusercontent.com/sportstimes/f1/main/_db/f2/{year}.json
"""

from __future__ import annotations

from typing import Any

from motorsport_calendar.models import (
    Championship,
    ChampionshipCategory,
    Circuit,
    Event,
    Session,
    SessionType,
)
from motorsport_calendar.providers.formula2.source import Formula2Source
from motorsport_calendar.providers.support_series.f1calendar_base import (
    F1CalendarBaseSource,
    _build_session,  # re-exported — imported directly by tests
)

__all__ = ["F1CalendarSource"]

# F2-specific: session key → (SessionType, duration minutes, display title)
# The dataset renamed two keys starting in 2025: "fp1" → "practice", "sprintRace" → "sprint".
# Both forms are kept here to support all seasons without breaking historical exports.
_SESSION_MAP: dict[str, tuple[SessionType, int, str]] = {
    "fp1": (SessionType.FP1, 45, "Free Practice"),  # dataset ≤ 2024
    "practice": (SessionType.FP1, 45, "Free Practice"),  # dataset ≥ 2025
    "qualifying": (SessionType.QUALIFYING, 30, "Qualifying"),
    "sprintRace": (SessionType.SPRINT, 45, "Sprint Race"),  # dataset ≤ 2024
    "sprint": (SessionType.SPRINT, 45, "Sprint Race"),  # dataset ≥ 2025
    "feature": (SessionType.RACE, 65, "Feature Race"),
}

# F2 circuit slug (f1calendar localeKey) → (country, IANA timezone)
_CIRCUIT_DATA: dict[str, tuple[str, str]] = {
    "albert_park": ("Australia", "Australia/Melbourne"),
    "americas": ("USA", "America/Chicago"),
    "bahrain": ("Bahrain", "Asia/Bahrain"),
    "baku": ("Azerbaijan", "Asia/Baku"),
    "barcelona": ("Spain", "Europe/Madrid"),
    "hungaroring": ("Hungary", "Europe/Budapest"),
    "imola": ("Italy", "Europe/Rome"),
    "jeddah": ("Saudi Arabia", "Asia/Riyadh"),
    "las_vegas": ("USA", "America/Los_Angeles"),
    "lusail": ("Qatar", "Asia/Qatar"),
    "marina_bay": ("Singapore", "Asia/Singapore"),
    "miami": ("USA", "America/New_York"),
    "monaco": ("Monaco", "Europe/Monaco"),
    "monza": ("Italy", "Europe/Rome"),
    "red_bull_ring": ("Austria", "Europe/Vienna"),
    "rodriguez": ("Mexico", "America/Mexico_City"),
    "shanghai": ("China", "Asia/Shanghai"),
    "silverstone": ("UK", "Europe/London"),
    "spa": ("Belgium", "Europe/Brussels"),
    "suzuka": ("Japan", "Asia/Tokyo"),
    "villeneuve": ("Canada", "America/Montreal"),
    "yas_marina": ("UAE", "Asia/Dubai"),
    "zandvoort": ("Netherlands", "Europe/Amsterdam"),
}

_FALLBACK_COUNTRY = "Unknown"
_FALLBACK_TIMEZONE = "UTC"


class F1CalendarSource(F1CalendarBaseSource, Formula2Source):
    """Formula 2 source backed by the f1calendar open dataset.

    Inherits all HTTP, cache, and mapping logic from F1CalendarBaseSource.
    The four properties below are the only F2-specific configuration.
    """

    @property
    def _series_key(self) -> str:
        return "f2"

    @property
    def _session_map(self) -> dict[str, tuple[SessionType, int, str]]:
        return _SESSION_MAP

    @property
    def _circuit_data(self) -> dict[str, tuple[str, str]]:
        return _CIRCUIT_DATA

    def _make_championship(self, year: int) -> Championship:
        return _make_championship(year)


# ---------------------------------------------------------------------------
# Module-level helpers — F2-specific, kept for direct use in unit tests.
# The generic equivalents live as instance methods in F1CalendarBaseSource.
# ---------------------------------------------------------------------------


def _make_championship(year: int) -> Championship:
    return Championship(
        id=f"formula2-{year}",
        name="FIA Formula 2 Championship",
        category=ChampionshipCategory.SINGLE_SEATER,
    )


def _resolve_circuit_data(slug: str) -> tuple[str, str]:
    return _CIRCUIT_DATA.get(slug, (_FALLBACK_COUNTRY, _FALLBACK_TIMEZONE))


def _build_circuit(event_data: dict[str, Any]) -> Circuit:
    slug: str = event_data.get("slug", "")
    country, timezone = _resolve_circuit_data(slug)
    return Circuit(
        id=f"f1calendar-f2-{slug}",
        name=event_data.get("name", slug),
        city=event_data.get("location", slug),
        country=country,
        timezone=timezone,
    )


def _build_event(championship: Championship, event_data: dict[str, Any], year: int) -> Event:
    circuit = _build_circuit(event_data)
    sessions: list[Session] = []
    raw_sessions: dict[str, Any] = event_data.get("sessions", {})
    for key, (session_type, duration, title) in _SESSION_MAP.items():
        if key in raw_sessions:
            session = _build_session(raw_sessions[key], session_type, duration, title)
            if session is not None:
                sessions.append(session)
    sessions.sort(key=lambda s: s.start_datetime)
    round_number: int = int(event_data.get("round", 0))
    return Event(
        championship=championship,
        season=year,
        round=round_number,
        name=event_data.get("name", ""),
        circuit=circuit,
        sessions=tuple(sessions),
        event_uid=f"f1calendar-f2-{year}-{round_number}@motorsport-calendar",
    )
