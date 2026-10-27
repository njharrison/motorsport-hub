"""Season explorer — pure logic to list, sort, and group the current
selection's events by month.

No Flet, no I/O: fetching lives in ``controller.get_calendar_year_events``
(Sprint 40). This module only turns already-fetched events into a
display-ready, chronologically sorted, month-grouped list — mirrors
``calendar_selection.py``'s own "compute" role, same "fetch" (controller)
vs "compute" (this module) split already established by
``upcoming_weekend.py``/``dashboard.py``.

Sprint 41: "Mon calendrier" gains a season explorer alongside the selection
summary (Sprint 40) — before generating an ICS, the user can browse every
event in the current year/championship selection, one row per event (name,
championship, circuit, country, date), sorted chronologically and grouped
by month. Reuses ``event_display.normalize_event_display`` (Sprint 32,
ADR-023) for the exact same name/circuit/country normalization rules
already used by ``ChampionshipCard`` — never re-implements them, and never
shows "Unknown" or a duplicate line.

Grouping/sorting is anchored on each event's earliest session start,
converted to UTC — same convention as ``upcoming_weekend._session_utc_date``
(a known, already-documented limitation for circuits far from UTC, not a
new one introduced here). An event with no sessions has no date and is
excluded — it cannot be placed chronologically.

Sprint 42: each row carries ``championship_id``/``event_uid`` — the two
identifiers needed to look the underlying ``Event`` back up in
``year_events`` when a row is clicked, opening the "fiche événement"
(``gui/event_details.py``). Deliberately *not* the raw ``Event`` itself:
this module's rows stay display-ready data, exactly like every other
dataclass in this package (``SelectionSummary``, ``NextRaceStart``, ...) —
the lookup is main_view.py's job, the same place that already owns
``year_events``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from motorsport_calendar.gui.display_names import get_display_name
from motorsport_calendar.gui.event_display import normalize_event_display
from motorsport_calendar.models import Event

_MONTH_LABELS_FR: tuple[str, ...] = (
    "Janvier",
    "Février",
    "Mars",
    "Avril",
    "Mai",
    "Juin",
    "Juillet",
    "Août",
    "Septembre",
    "Octobre",
    "Novembre",
    "Décembre",
)

_DAY_LABELS_FR: tuple[str, ...] = (
    "Lundi",
    "Mardi",
    "Mercredi",
    "Jeudi",
    "Vendredi",
    "Samedi",
    "Dimanche",
)


@dataclass(frozen=True)
class SeasonEventRow:
    """One event, display-ready — a single row in the season explorer.

    ``circuit_name``/``country`` are ``None`` when that line should be
    hidden entirely — never an empty string, never the literal "Unknown"
    (same contract as ``event_display.EventDisplayData``).

    ``championship_id``/``event_uid`` (Sprint 42) are not rendered — they
    are carried through so a click handler can look the underlying
    ``Event`` back up in ``year_events`` and open its "fiche événement",
    without this module ever needing to know that clicking is possible
    (same "identity carried, never interpreted" pattern as
    ``ChampionshipCardData.championship_id``, Sprint 30).
    """

    event_name: str
    championship_name: str
    circuit_name: str | None
    country: str | None
    date_label: str  # e.g. "Dimanche 06/12" — already formatted, UTC-anchored
    championship_id: str
    event_uid: str


@dataclass(frozen=True)
class SeasonMonthGroup:
    """Events sharing a calendar month, already sorted chronologically."""

    month_label: str  # e.g. "Décembre 2025"
    rows: tuple[SeasonEventRow, ...]


def _earliest_start(event: Event) -> datetime | None:
    starts = [s.start_datetime for s in event.sessions]
    return min(starts) if starts else None


def _month_label(year: int, month: int) -> str:
    return f"{_MONTH_LABELS_FR[month - 1]} {year}"


def _date_label(start: datetime) -> str:
    local = start.astimezone(UTC)
    return f"{_DAY_LABELS_FR[local.weekday()]} {local:%d/%m}"


def build_season_explorer(
    year_events: dict[str, list[Event]], selected_championships: list[str]
) -> tuple[SeasonMonthGroup, ...]:
    """Turn the current selection into a chronological, month-grouped list.

    Args:
        year_events: every registered championship's events for the
            browsed year, keyed by registry championship id — see
            ``controller.get_calendar_year_events``. Championships not in
            *selected_championships* are simply ignored, never re-fetched.
        selected_championships: the user's current checkbox selection
            (``GenerateState.selected_championships``).

    Returns an empty tuple when nothing is selected, or when the selected
    championships have no events with sessions for the browsed year —
    never a partially-built result.
    """
    dated: list[tuple[datetime, str, Event]] = []
    for cid in selected_championships:
        for event in year_events.get(cid, []):
            start = _earliest_start(event)
            if start is not None:
                dated.append((start, cid, event))

    dated.sort(key=lambda item: item[0])

    groups: list[SeasonMonthGroup] = []
    current_key: tuple[int, int] | None = None
    current_rows: list[SeasonEventRow] = []

    for start, cid, event in dated:
        utc_start = start.astimezone(UTC)
        key = (utc_start.year, utc_start.month)
        if key != current_key:
            if current_key is not None:
                groups.append(SeasonMonthGroup(_month_label(*current_key), tuple(current_rows)))
            current_key = key
            current_rows = []
        display = normalize_event_display(cid, event)
        current_rows.append(
            SeasonEventRow(
                event_name=display.grand_prix_name,
                championship_name=get_display_name(cid),
                circuit_name=display.circuit_name,
                country=display.country,
                date_label=_date_label(start),
                championship_id=cid,
                event_uid=event.event_uid,
            )
        )

    if current_key is not None:
        groups.append(SeasonMonthGroup(_month_label(*current_key), tuple(current_rows)))

    return tuple(groups)
