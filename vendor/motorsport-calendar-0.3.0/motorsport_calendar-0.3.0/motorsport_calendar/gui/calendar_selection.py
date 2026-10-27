"""Mon calendrier — pure logic to summarize the current year/championship selection.

No Flet, no I/O: fetching lives in ``controller.get_calendar_year_events``. This
module only turns already-fetched events into a display-ready summary, so it
is fully unit-testable with plain ``Event``/``Session`` fixtures — no HTTP
mocking needed. Mirrors ``upcoming_weekend.py``/``dashboard.py``'s own
separation of "fetch" (controller) vs "compute" (this module).

Sprint 40: "Mon calendrier" becomes a browsable calendar, not just a
generation wizard — this summary (event/session counts, period covered) is
what turns "filter by year" + "filter by championship" into live,
explorable feedback, shown before the user ever reaches "Créer mon
calendrier". Every registered championship's events for the browsed year
are fetched once (``controller.get_calendar_year_events``); toggling a
championship checkbox is then a purely local computation over
already-fetched data — no network call per toggle.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from motorsport_calendar.models import Event


@dataclass(frozen=True)
class SelectionSummary:
    """Everything the "Mon calendrier" summary widget needs — pure data.

    ``period_start``/``period_end`` are ``None`` exactly when
    ``event_count`` is 0 — no selection, or a selection whose championships
    have no events for the browsed year — never a half-populated summary.
    """

    event_count: int
    session_count: int
    period_start: date | None
    period_end: date | None


def build_selection_summary(
    year_events: dict[str, list[Event]], selected_championships: list[str]
) -> SelectionSummary:
    """Aggregate *year_events* for exactly the championships the user selected.

    Args:
        year_events: every registered championship's events for the
            currently browsed year, keyed by registry championship id — see
            ``controller.get_calendar_year_events``. Championships not in
            *selected_championships* are simply ignored, never re-fetched.
        selected_championships: the user's current checkbox selection
            (``GenerateState.selected_championships``).
    """
    events: list[Event] = [
        event for cid in selected_championships for event in year_events.get(cid, [])
    ]
    if not events:
        return SelectionSummary(event_count=0, session_count=0, period_start=None, period_end=None)

    session_count = sum(len(e.sessions) for e in events)
    starts = [s.start_datetime for e in events for s in e.sessions]
    if not starts:
        return SelectionSummary(
            event_count=len(events),
            session_count=0,
            period_start=None,
            period_end=None,
        )

    return SelectionSummary(
        event_count=len(events),
        session_count=session_count,
        period_start=min(starts).date(),
        period_end=max(starts).date(),
    )
