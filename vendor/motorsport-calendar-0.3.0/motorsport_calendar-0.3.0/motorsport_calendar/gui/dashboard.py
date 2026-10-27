"""Tableau de bord — pure logic to aggregate season-wide + weekend stats.

No Flet, no I/O: fetching lives in ``controller.get_dashboard_data`` (which
reuses the exact same fetch pipeline as ``get_upcoming_weekend`` — see
``controller._fetch_weekend_entries``). This module only turns
already-fetched entries into a display-ready result, so it is fully
unit-testable with plain ``Event``/``Session`` fixtures — no HTTP mocking
needed. Mirrors ``upcoming_weekend.py``'s own separation of "fetch"
(controller) vs "compute" (this module).

Sprint 39: the Dashboard becomes the app's home page. It deliberately
reuses ``upcoming_weekend.find_upcoming_weekend`` for the "prochain
week-end" + "championnats présents ce week-end" stats instead of
re-implementing weekend-finding — "Ce week-end" and the Dashboard always
agree on what the next race weekend is, by construction.

Sprint 44: ``build_dashboard_data`` accepts an optional ``favorite_ids``,
forwarded as-is to ``find_upcoming_weekend`` — favorited championships are
shown first in ``DashboardData.weekend.cards``, the exact same "favorites
first" logic "Ce week-end" uses (never a second implementation).

Sprint 53: the Dashboard becomes the app's real home page (not just its
first tab) — ``DashboardData`` grows 5 fields for the "Nouveautés"/"État
de Motorsport Calendar" sections, all passthrough values resolved by
``controller.get_dashboard_data`` (registry/config/FavoritesService/
UpdateService — never a new service, per the sprint brief), except
``functional_providers``, genuinely computed here from *entries* (the one
new field that IS "aggregate stats from already-fetched entries", this
module's actual job).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from motorsport_calendar.gui.display_names import get_display_name
from motorsport_calendar.gui.upcoming_weekend import (
    WeekendEntry,
    WeekendResult,
    find_upcoming_weekend,
    format_session_datetime,
)
from motorsport_calendar.gui.update_service import UpdateCheckResult
from motorsport_calendar.models import SessionType


@dataclass(frozen=True)
class NextRaceStart:
    """The next RACE-type session across every fetched championship.

    Deliberately RACE only, not SPRINT/HYPERPOLE — "le prochain départ"
    reads as the next Grand Prix/Course start, not any track session.
    """

    championship_name: str
    display: str  # e.g. "Dimanche 12/07 15:00" — already formatted, circuit-local time


@dataclass(frozen=True)
class DashboardData:
    """Everything the Dashboard view needs — pure presentation data.

    Fields:
        total_championships:  registered count (``registry.list_all()``)
                               — every provider, including stubs.
        active_championships: enabled count (``registry.enabled(config.
                               providers)``) — a provider disabled via
                               ``config.yaml`` no longer counts here, even
                               though it stays "registered" (Sprint 53).
        functional_providers: distinct championship ids that actually
                               returned at least one fetched event across
                               the two fetched years (Sprint 53) — a
                               provider that always raises (IMSA/WorldSBK
                               stubs) never contributes an entry, so never
                               counts here either; the honest gap between
                               this and ``active_championships`` is the
                               whole point of showing both.
        favorite_count:        ``len(FavoritesService().list())``.
        current_version:       ``motorsport_calendar.__version__``.
        update:                the same ``UpdateCheckResult`` the Sprint 51
                                startup dialog already computes (see
                                ``controller.check_for_update``) — reused
                                as-is, never recomputed with different logic.
    """

    total_championships: int
    total_events_season: int
    total_sessions_season: int
    weekend: WeekendResult
    next_race: NextRaceStart | None
    active_championships: int = 0
    functional_providers: int = 0
    favorite_count: int = 0
    current_version: str = ""
    update: UpdateCheckResult | None = None


def _find_next_race(entries: list[WeekendEntry], *, now: datetime) -> NextRaceStart | None:
    candidates: list[tuple[datetime, WeekendEntry]] = [
        (session.start_datetime, entry)
        for entry in entries
        for session in entry.event.sessions
        if session.type is SessionType.RACE and session.start_datetime >= now
    ]
    if not candidates:
        return None
    start, entry = min(candidates, key=lambda c: c[0])
    return NextRaceStart(
        championship_name=get_display_name(entry.championship_id),
        display=format_session_datetime(start, entry.event.circuit.timezone),
    )


def build_dashboard_data(
    entries: list[WeekendEntry],
    *,
    total_championships: int,
    now: datetime,
    favorite_ids: frozenset[str] = frozenset(),
    active_championships: int = 0,
    favorite_count: int = 0,
    current_version: str = "",
    update: UpdateCheckResult | None = None,
) -> DashboardData:
    """Top-level entry point: aggregate everything the Dashboard needs.

    Args:
        entries: every championship/event fetched for *now*'s year and the
            following one — see ``controller._fetch_weekend_entries``.
        total_championships: count of all registered championship IDs
            (``registry.list_all()``), independent of how many actually
            returned events (a stub like WEC/IMSA/WorldSBK still counts as
            "available").
        now: reference instant — same one used to fetch *entries* and to
            find the next weekend.
        favorite_ids: favorited championship ids (Sprint 44) — forwarded
            to ``find_upcoming_weekend`` so a weekend containing a
            favorite shows it first among ``weekend.cards``.
        active_championships: count of enabled providers (Sprint 53,
            ``registry.enabled(config.providers)``) — passthrough, same
            "caller already knows this" convention as
            *total_championships*.
        favorite_count: ``len(favorite_ids)`` — passthrough (Sprint 53);
            kept separate from *favorite_ids* itself since the latter is
            only needed for weekend-card ordering, not for display.
        current_version: ``motorsport_calendar.__version__`` — passthrough
            (Sprint 53).
        update: the Sprint 51 update-check result — passthrough
            (Sprint 53), reused as-is for the "Nouveautés" section.
    """
    weekend = find_upcoming_weekend(entries, now=now, favorite_ids=favorite_ids)
    season_entries = [e for e in entries if e.event.season == now.year]
    total_events = len(season_entries)
    total_sessions = sum(len(e.event.sessions) for e in season_entries)
    next_race = _find_next_race(entries, now=now)
    # The one genuinely-computed-here Sprint 53 stat: a provider that
    # always raises (IMSA/WorldSBK stubs) never contributes an entry to
    # `entries` across either fetched year, so it never counts here — no
    # new provider capability flag invented, just what was already fetched.
    functional_providers = len({entry.championship_id for entry in entries})
    return DashboardData(
        total_championships=total_championships,
        total_events_season=total_events,
        total_sessions_season=total_sessions,
        weekend=weekend,
        next_race=next_race,
        active_championships=active_championships,
        functional_providers=functional_providers,
        favorite_count=favorite_count,
        current_version=current_version,
        update=update,
    )
