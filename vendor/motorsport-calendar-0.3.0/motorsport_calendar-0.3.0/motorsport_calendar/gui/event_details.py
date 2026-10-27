"""Event details — pure logic to build the "fiche événement" for one event.

No Flet, no I/O: the event is already fetched (it lives in ``year_events``,
built by ``controller.get_calendar_year_events``, Sprint 40) — this module
only turns it into display-ready data, so it is fully unit-testable with
plain ``Event``/``Session`` fixtures.

Sprint 42: clicking an event row in the season explorer (Sprint 41) opens
this fiche — championship, event name, circuit, country, date, and the
chronological list of sessions (type + time). Reuses existing models
end-to-end rather than inventing new ones:

- ``event_display.normalize_event_display`` (Sprint 32, ADR-023) for the
  event name / circuit / country — never "Unknown", never a duplicate line.
- ``event_display.session_type_label`` (Sprint 42) for each session's
  French label — the exact same vocabulary already used by "Ce week-end".
- ``components.championship_card.ChampionshipCardData``/``SessionRow``
  (Sprint 30) as the fiche's own data model for
  championship/event/circuit/country/sessions — the "réutiliser les
  modèles existants" instruction is taken literally: this module builds
  that model, it does not redefine it. The one field that model does not
  carry — a single event-level date headline, distinct from each session's
  own time — is added here as ``EventDetails.date_label``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from motorsport_calendar.gui.components.championship_card import ChampionshipCardData, SessionRow
from motorsport_calendar.gui.display_names import get_display_name
from motorsport_calendar.gui.event_display import normalize_event_display, session_type_label
from motorsport_calendar.models import Event

# Same French weekday names as upcoming_weekend.py — duplicated rather than
# imported (it is a private module-level constant there, and this 7-string
# table is trivial, static vocabulary, not logic worth coupling two modules
# over; same call already made for gui/season_explorer.py in Sprint 41).
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
class EventDetails:
    """Everything the "fiche événement" (Sprint 42) needs — pure data.

    ``card`` reuses the exact ``ChampionshipCardData``/``SessionRow`` model
    already used by ``ChampionshipCard`` (Sprint 30) for
    championship/event/circuit/country/sessions — never redefined here, so
    the fiche's session list renders through the exact same, already-tested
    component as "Ce week-end".

    ``date_label`` is the one extra field that model does not carry: a
    single event-level date headline (the card itself only shows
    per-session times). ``None`` when the event has no sessions at all —
    nothing to anchor a date on, mirroring ``SelectionSummary``'s
    ``period_start``/``period_end`` "None means nothing to show" contract
    (Sprint 40).

    ``circuit_key`` (Sprint 47) is the circuit's stable identity, in
    lockstep with ``card.circuit_name``: ``None`` exactly when there is no
    circuit line to click (hidden as redundant with the headline for this
    event) — never interpreted here, only carried through for
    ``main_view.py`` to look up the "fiche Circuit" via
    ``gui/circuit_service.py`` when the circuit name is clicked.
    """

    card: ChampionshipCardData
    date_label: str | None
    circuit_key: str | None


def _circuit_zone(circuit_timezone: str) -> ZoneInfo:
    try:
        return ZoneInfo(circuit_timezone)
    except (ZoneInfoNotFoundError, ValueError):
        return ZoneInfo("UTC")


def _weekday_time(start: datetime, tz: ZoneInfo) -> str:
    local = start.astimezone(tz)
    return f"{_DAY_LABELS_FR[local.weekday()]} {local:%H:%M}"


def _date_label(start: datetime, tz: ZoneInfo) -> str:
    local = start.astimezone(tz)
    return f"{_DAY_LABELS_FR[local.weekday()]} {local:%d/%m/%Y}"


def build_event_details(championship_id: str, event: Event) -> EventDetails:
    """Turn *event* into a display-ready "fiche événement".

    Args:
        championship_id: the registry id *event* was fetched with (e.g.
            ``"formula1"``) — never ``event.championship.id``, which is
            provider-internal and year-suffixed (same rule as every other
            module in this package since Sprint 29).
        event: the raw fetched event. Never mutated.

    Sessions are sorted chronologically by their own start time — a
    provider's own ordering is never trusted (same rule as
    ``upcoming_weekend._build_card``).
    """
    tz = _circuit_zone(event.circuit.timezone)
    sessions = sorted(event.sessions, key=lambda s: s.start_datetime)

    display = normalize_event_display(championship_id, event)
    card = ChampionshipCardData(
        championship_id=championship_id,
        championship_name=get_display_name(championship_id),
        event_name=display.grand_prix_name,
        circuit_name=display.circuit_name,
        country=display.country,
        sessions=tuple(
            SessionRow(
                label=session_type_label(session),
                day_time=_weekday_time(session.start_datetime, tz),
            )
            for session in sessions
        ),
    )

    date_label = _date_label(sessions[0].start_datetime, tz) if sessions else None
    return EventDetails(card=card, date_label=date_label, circuit_key=display.circuit_key)
