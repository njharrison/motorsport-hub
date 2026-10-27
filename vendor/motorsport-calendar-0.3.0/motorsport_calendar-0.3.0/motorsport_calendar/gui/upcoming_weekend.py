"""Ce week-end — pure logic to find and format the next race weekend.

No Flet, no I/O: fetching lives in ``controller.get_upcoming_weekend`` (which
mirrors ``generate_calendar``'s pipeline). This module only turns
already-fetched events into a display-ready result, so it is fully
unit-testable with plain ``Event``/``Session`` fixtures — no HTTP mocking
needed.

Intentionally lives in the GUI layer only, like ``categories.py`` and
``display_names.py``: French session/country labels are presentation
concerns, never part of the domain models.

Important: every provider's ``Championship.id`` on a fetched ``Event`` is
year-suffixed (e.g. ``"formula1-2026"``), not the plain registry id
(``"formula1"``) that ``categories.py``/``display_names.py`` expect. This
module therefore never reads ``event.championship.id`` for grouping or
display — the caller (``controller.get_upcoming_weekend``) already knows
the registry id it fetched with, and passes it alongside each event as a
``WeekendEntry``.

Sprint 30: the card shape (``ChampionshipCardData``/``SessionRow``) moved to
``gui/components/championship_card.py`` — the reusable ChampionshipCard
component's own model. This module builds that model but no longer defines
it, so any future screen (Favoris, Recherche, ...) can produce the exact
same model without depending on "Ce week-end" at all.

Sprint 32: event *metadata* normalization (which Grand Prix name, circuit,
and country to show — never "Unknown", never a duplicate line) moved to
``gui/event_display.py``. This module only fetches/finds/groups events and
delegates formatting each one's metadata to that module.

Sprint 42: session-type French labels (``_SESSION_LABELS``/
``_session_type_label``) moved to ``gui/event_display.py`` as the public
``session_type_label()`` once ``gui/event_details.py`` needed the exact same
mapping — same "mutualize on the second real use" principle as Sprint 32.

Sprint 44: ``find_upcoming_weekend``/``_group_entries_for_display`` accept
an optional ``favorite_ids`` — favorited championships are pulled to the
front of the card list (a stable sort on top of the existing
category-based order), shared by both "Ce week-end" and the Dashboard
(``gui/dashboard.py::build_dashboard_data`` calls this same function) so
there is exactly one "favorites first" implementation, never two.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from motorsport_calendar.gui.categories import get_groups_for
from motorsport_calendar.gui.components.championship_card import (
    ChampionshipCardData,
    SessionRow,
)
from motorsport_calendar.gui.display_names import get_display_name
from motorsport_calendar.gui.event_display import normalize_event_display, session_type_label
from motorsport_calendar.models import Event, Session

# ---------------------------------------------------------------------------
# Championships considered — fixed list, independent of config.yaml opt-out.
# ---------------------------------------------------------------------------

WEEKEND_CHAMPIONSHIP_IDS: tuple[str, ...] = (
    "formula1",
    "formula2",
    "formula3",
    "f1-academy",
    "formula-e",
    "wec",
    "elms",
    "mlmc",
    "imsa",
    "gtwc-europe",
    "gtwc-america",
    "gtwc-asia",
    "igtc",
    "motogp",
    "moto2",
    "moto3",
    "worldsbk",
)

# ---------------------------------------------------------------------------
# French labels — presentation only, same philosophy as display_names.py.
# ---------------------------------------------------------------------------

_DAY_LABELS_FR: tuple[str, ...] = (
    "Lundi",
    "Mardi",
    "Mercredi",
    "Jeudi",
    "Vendredi",
    "Samedi",
    "Dimanche",
)

_UTC = UTC


def _circuit_zone(circuit_timezone: str) -> ZoneInfo:
    try:
        return ZoneInfo(circuit_timezone)
    except (ZoneInfoNotFoundError, ValueError):
        return ZoneInfo("UTC")


def format_session_datetime(start: datetime, circuit_timezone: str) -> str:
    """ "{Jour} {JJ/MM} {HH:MM}" in the circuit's local timezone.

    Public since Sprint 39: ``gui/dashboard.py`` reuses this for its
    standalone "prochain départ" headline stat, which — unlike a session
    row inside a ChampionshipCard (already scoped to a known weekend) —
    needs the date spelled out, not just the day name.
    """
    local = start.astimezone(_circuit_zone(circuit_timezone))
    return f"{_DAY_LABELS_FR[local.weekday()]} {local:%d/%m} {local:%H:%M}"


@dataclass(frozen=True)
class WeekendEntry:
    """An event paired with the registry championship id it was fetched
    with (e.g. ``"formula1"``) — ``event.championship.id`` is provider
    internal (year-suffixed) and unreliable for grouping/display.
    """

    championship_id: str
    event: Event


@dataclass(frozen=True)
class WeekendResult:
    """Outcome of the "Ce week-end" search — exactly the 3 states the view needs."""

    found: bool
    friday: date | None = None
    sunday: date | None = None
    cards: tuple[ChampionshipCardData, ...] = ()
    next_hint_date: date | None = None


# ---------------------------------------------------------------------------
# Finding the next weekend with at least one competition
# ---------------------------------------------------------------------------


def _weekend_bounds_containing_or_after(day: date) -> tuple[date, date]:
    """Friday/Sunday (inclusive, UTC calendar dates) of the week containing
    *day*, or the following week's if *day* is already past that Sunday.
    """
    friday = day - timedelta(days=(day.weekday() - 4) % 7)
    sunday = friday + timedelta(days=2)
    if day > sunday:
        friday += timedelta(days=7)
        sunday += timedelta(days=7)
    return friday, sunday


def _session_utc_date(session: Session) -> date:
    return session.start_datetime.astimezone(_UTC).date()


def _event_in_window(event: Event, friday: date, sunday: date) -> bool:
    return any(friday <= _session_utc_date(s) <= sunday for s in event.sessions)


def _entry_earliest_start(entry: WeekendEntry) -> datetime:
    return min(
        (s.start_datetime for s in entry.event.sessions),
        default=datetime.max.replace(tzinfo=_UTC),
    )


def find_next_weekend_entries(
    entries: list[WeekendEntry],
    *,
    now: datetime,
    max_weeks_ahead: int = 104,
) -> tuple[date, date, list[WeekendEntry]] | None:
    """Scan forward week by week from *now* for the next Friday-Sunday
    (UTC) window containing at least one session, across *entries*.

    Returns (friday, sunday, matching_entries) — matching_entries sorted
    chronologically by each event's earliest session — or ``None`` if no
    window within *max_weeks_ahead* contains any session.
    """
    friday, sunday = _weekend_bounds_containing_or_after(now.date())

    for _ in range(max_weeks_ahead):
        matches = [e for e in entries if _event_in_window(e.event, friday, sunday)]
        if matches:
            matches.sort(key=_entry_earliest_start)
            return friday, sunday, matches
        friday += timedelta(days=7)
        sunday += timedelta(days=7)

    return None


def _next_hint_date(entries: list[WeekendEntry], *, now: datetime) -> date | None:
    future_starts = [
        s.start_datetime
        for entry in entries
        for s in entry.event.sessions
        if s.start_datetime >= now
    ]
    return min(future_starts).date() if future_starts else None


# ---------------------------------------------------------------------------
# Grouping for display: Formula then Endurance, chronological within each.
# ---------------------------------------------------------------------------


def _group_entries_for_display(
    entries: list[WeekendEntry], favorite_ids: frozenset[str] = frozenset()
) -> list[WeekendEntry]:
    """*entries* is already chronologically sorted; partition into Formula
    then Endurance (per categories.py), preserving chronological order
    within each partition — reuses the existing grouping helper as-is.

    Sprint 44: when *favorite_ids* is non-empty, a second stable partition
    pulls favorited championships to the front — a favorite entry keeps its
    position relative to other favorites (still category/chronological
    order among themselves), it just moves ahead of every non-favorite.
    """
    available_ids = [entry.championship_id for entry in entries]
    ordered: list[WeekendEntry] = []
    for _group, ids_in_group in get_groups_for(available_ids):
        ids_set = set(ids_in_group)
        ordered.extend(e for e in entries if e.championship_id in ids_set)
    if favorite_ids:
        ordered.sort(key=lambda e: e.championship_id not in favorite_ids)
    return ordered


def _build_card(entry: WeekendEntry) -> ChampionshipCardData:
    event = entry.event
    tz = _circuit_zone(event.circuit.timezone)
    sessions = sorted(event.sessions, key=lambda s: s.start_datetime)
    rows = tuple(
        SessionRow(
            label=session_type_label(session),
            day_time=(
                f"{_DAY_LABELS_FR[session.start_datetime.astimezone(tz).weekday()]} "
                f"{session.start_datetime.astimezone(tz):%H:%M}"
            ),
        )
        for session in sessions
    )
    display = normalize_event_display(entry.championship_id, event)
    return ChampionshipCardData(
        championship_id=entry.championship_id,
        championship_name=get_display_name(entry.championship_id),
        event_name=display.grand_prix_name,
        circuit_name=display.circuit_name,
        country=display.country,
        sessions=rows,
    )


def find_upcoming_weekend(
    entries: list[WeekendEntry],
    *,
    now: datetime,
    max_weeks_ahead: int = 104,
    favorite_ids: frozenset[str] = frozenset(),
) -> WeekendResult:
    """Top-level entry point: search, group, and format in one call.

    Args:
        favorite_ids: favorited championship ids (Sprint 44) —
            ``controller.get_upcoming_weekend``/``get_dashboard_data``
            source these from ``FavoritesService``. Favorited
            championships are shown first among the returned cards.
    """
    found = find_next_weekend_entries(entries, now=now, max_weeks_ahead=max_weeks_ahead)
    if found is None:
        return WeekendResult(found=False, next_hint_date=_next_hint_date(entries, now=now))

    friday, sunday, matches = found
    ordered = _group_entries_for_display(matches, favorite_ids)
    cards = tuple(_build_card(e) for e in ordered)
    return WeekendResult(found=True, friday=friday, sunday=sunday, cards=cards)
