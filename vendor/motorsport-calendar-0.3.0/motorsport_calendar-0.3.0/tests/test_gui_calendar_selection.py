"""Tests for gui.calendar_selection — pure logic, no Flet, no HTTP.

Mirrors test_gui_dashboard.py's style: plain Event/Session fixtures, no HTTP
mocking needed (fetching lives in controller.get_calendar_year_events).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from motorsport_calendar.gui.calendar_selection import SelectionSummary, build_selection_summary
from motorsport_calendar.models import (
    Championship,
    ChampionshipCategory,
    Circuit,
    Event,
    Session,
    SessionType,
)


def _session(session_type: SessionType, start: datetime, *, minutes: int = 60) -> Session:
    return Session(
        type=session_type,
        start_datetime=start,
        end_datetime=start + timedelta(minutes=minutes),
        title=session_type.value,
    )


def _event(
    championship_id: str,
    *,
    name: str = "Grand Prix",
    round_: int = 1,
    season: int = 2026,
    sessions: tuple[Session, ...] = (),
) -> Event:
    championship = Championship(
        id=f"{championship_id}-9999",
        name=championship_id,
        category=ChampionshipCategory.SINGLE_SEATER,
    )
    circuit = Circuit(
        id=name.lower().replace(" ", "-"),
        name=name,
        city=name,
        country="France",
        timezone="Europe/Paris",
    )
    return Event(
        championship=championship,
        season=season,
        round=round_,
        name=name,
        circuit=circuit,
        sessions=sessions,
        event_uid=f"{championship_id}-{round_}@test",
    )


class TestBuildSelectionSummaryEmptySelection:
    def test_no_championships_selected_returns_zeroed_summary(self) -> None:
        year_events = {
            "formula1": [
                _event(
                    "formula1",
                    sessions=(_session(SessionType.RACE, datetime(2026, 3, 1, 14, 0, tzinfo=UTC)),),
                )
            ]
        }
        summary = build_selection_summary(year_events, [])
        assert summary == SelectionSummary(
            event_count=0, session_count=0, period_start=None, period_end=None
        )

    def test_empty_year_events_returns_zeroed_summary(self) -> None:
        summary = build_selection_summary({}, ["formula1"])
        assert summary == SelectionSummary(
            event_count=0, session_count=0, period_start=None, period_end=None
        )

    def test_selected_championship_with_no_fetched_events_ignored(self) -> None:
        """A championship whose fetch failed (absent from year_events) is
        simply skipped, not an error — matches controller's partial-failure
        resilience rule."""
        summary = build_selection_summary({}, ["wec"])
        assert summary.event_count == 0


class TestBuildSelectionSummarySingleChampionship:
    def test_counts_events_and_sessions_for_one_championship(self) -> None:
        year_events = {
            "formula1": [
                _event(
                    "formula1",
                    round_=1,
                    sessions=(
                        _session(SessionType.FP1, datetime(2026, 3, 1, 10, 0, tzinfo=UTC)),
                        _session(SessionType.RACE, datetime(2026, 3, 1, 14, 0, tzinfo=UTC)),
                    ),
                ),
                _event(
                    "formula1",
                    round_=2,
                    sessions=(_session(SessionType.RACE, datetime(2026, 4, 5, 14, 0, tzinfo=UTC)),),
                ),
            ],
            "motogp": [
                _event(
                    "motogp",
                    sessions=(_session(SessionType.RACE, datetime(2026, 5, 1, 14, 0, tzinfo=UTC)),),
                )
            ],
        }
        summary = build_selection_summary(year_events, ["formula1"])
        assert summary.event_count == 2
        assert summary.session_count == 3

    def test_period_covers_earliest_to_latest_session(self) -> None:
        year_events = {
            "formula1": [
                _event(
                    "formula1",
                    round_=1,
                    sessions=(_session(SessionType.RACE, datetime(2026, 3, 1, 14, 0, tzinfo=UTC)),),
                ),
                _event(
                    "formula1",
                    round_=2,
                    sessions=(
                        _session(SessionType.RACE, datetime(2026, 11, 20, 14, 0, tzinfo=UTC)),
                    ),
                ),
            ]
        }
        summary = build_selection_summary(year_events, ["formula1"])
        assert summary.period_start == datetime(2026, 3, 1).date()
        assert summary.period_end == datetime(2026, 11, 20).date()

    def test_event_with_no_sessions_counted_but_no_period(self) -> None:
        year_events = {"formula1": [_event("formula1", sessions=())]}
        summary = build_selection_summary(year_events, ["formula1"])
        assert summary.event_count == 1
        assert summary.session_count == 0
        assert summary.period_start is None
        assert summary.period_end is None


class TestBuildSelectionSummaryMultipleChampionships:
    def test_aggregates_across_selected_championships(self) -> None:
        year_events = {
            "formula1": [
                _event(
                    "formula1",
                    sessions=(_session(SessionType.RACE, datetime(2026, 3, 1, 14, 0, tzinfo=UTC)),),
                )
            ],
            "motogp": [
                _event(
                    "motogp",
                    sessions=(
                        _session(SessionType.RACE, datetime(2026, 6, 1, 14, 0, tzinfo=UTC)),
                        _session(SessionType.SPRINT, datetime(2026, 5, 31, 14, 0, tzinfo=UTC)),
                    ),
                )
            ],
            "moto2": [
                _event(
                    "moto2",
                    sessions=(_session(SessionType.RACE, datetime(2026, 7, 1, 14, 0, tzinfo=UTC)),),
                )
            ],
        }
        summary = build_selection_summary(year_events, ["formula1", "motogp"])
        assert summary.event_count == 2
        assert summary.session_count == 3
        assert summary.period_start == datetime(2026, 3, 1).date()
        assert summary.period_end == datetime(2026, 6, 1).date()
        # moto2 not selected — must not contribute to the totals or period.

    def test_unfetched_championship_in_selection_does_not_crash(self) -> None:
        year_events = {
            "formula1": [
                _event(
                    "formula1",
                    sessions=(_session(SessionType.RACE, datetime(2026, 3, 1, 14, 0, tzinfo=UTC)),),
                )
            ]
        }
        summary = build_selection_summary(year_events, ["formula1", "wec"])
        assert summary.event_count == 1


class TestBuildSelectionSummaryAllDisciplines:
    def test_selecting_every_fetched_championship(self) -> None:
        year_events = {
            "formula1": [
                _event(
                    "formula1",
                    sessions=(_session(SessionType.RACE, datetime(2026, 3, 1, 14, 0, tzinfo=UTC)),),
                )
            ],
            "motogp": [
                _event(
                    "motogp",
                    sessions=(_session(SessionType.RACE, datetime(2026, 6, 1, 14, 0, tzinfo=UTC)),),
                )
            ],
            "wec": [
                _event(
                    "wec",
                    sessions=(_session(SessionType.RACE, datetime(2026, 9, 1, 14, 0, tzinfo=UTC)),),
                )
            ],
        }
        summary = build_selection_summary(year_events, list(year_events.keys()))
        assert summary.event_count == 3
        assert summary.session_count == 3
        assert summary.period_start == datetime(2026, 3, 1).date()
        assert summary.period_end == datetime(2026, 9, 1).date()
