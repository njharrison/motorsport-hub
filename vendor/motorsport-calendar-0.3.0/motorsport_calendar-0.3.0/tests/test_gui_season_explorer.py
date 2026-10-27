"""Tests for gui.season_explorer — pure logic, no Flet, no HTTP.

Mirrors test_gui_calendar_selection.py's style: plain Event/Session
fixtures, no HTTP mocking needed (fetching lives in
controller.get_calendar_year_events).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from motorsport_calendar.gui.season_explorer import SeasonMonthGroup, build_season_explorer
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
    circuit_name: str | None = None,
    circuit_city: str | None = None,
    country: str = "France",
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
        name=circuit_name if circuit_name is not None else name,
        city=circuit_city if circuit_city is not None else name,
        country=country,
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


class TestBuildSeasonExplorerEmpty:
    def test_no_championships_selected_returns_empty_tuple(self) -> None:
        year_events = {
            "formula1": [
                _event(
                    "formula1",
                    sessions=(_session(SessionType.RACE, datetime(2026, 3, 1, 14, 0, tzinfo=UTC)),),
                )
            ]
        }
        groups = build_season_explorer(year_events, [])
        assert groups == ()

    def test_empty_year_events_returns_empty_tuple(self) -> None:
        groups = build_season_explorer({}, ["formula1"])
        assert groups == ()

    def test_selected_championship_with_no_fetched_events_ignored(self) -> None:
        groups = build_season_explorer({}, ["wec"])
        assert groups == ()

    def test_event_with_no_sessions_excluded(self) -> None:
        """An event with no sessions has no date and cannot be placed
        chronologically — excluded rather than crashing."""
        year_events = {"formula1": [_event("formula1", sessions=())]}
        groups = build_season_explorer(year_events, ["formula1"])
        assert groups == ()


class TestBuildSeasonExplorerSingleChampionship:
    def test_event_fields_are_normalized_and_populated(self) -> None:
        year_events = {
            "formula1": [
                _event(
                    "formula1",
                    name="Belgian",
                    circuit_name="Spa-Francorchamps",
                    circuit_city="Spa",
                    country="Belgium",
                    sessions=(
                        _session(SessionType.RACE, datetime(2026, 7, 12, 14, 0, tzinfo=UTC)),
                    ),
                )
            ]
        }
        groups = build_season_explorer(year_events, ["formula1"])
        assert len(groups) == 1
        row = groups[0].rows[0]
        assert row.event_name == "Belgian Grand Prix"  # GP suffix rule, ADR-023
        assert row.championship_name == "Formula 1"
        assert row.circuit_name == "Spa-Francorchamps"
        assert row.country == "🇧🇪 Belgique"
        assert row.date_label == "Dimanche 12/07"

    def test_row_carries_identity_for_click_to_detail(self) -> None:
        """Sprint 42: championship_id/event_uid let a click handler look
        the Event back up in year_events — never the Event itself."""
        event = _event(
            "formula1",
            round_=7,
            sessions=(_session(SessionType.RACE, datetime(2026, 7, 12, 14, 0, tzinfo=UTC)),),
        )
        year_events = {"formula1": [event]}
        groups = build_season_explorer(year_events, ["formula1"])
        row = groups[0].rows[0]
        assert row.championship_id == "formula1"
        assert row.event_uid == event.event_uid == "formula1-7@test"

    def test_single_event_produces_single_month_group(self) -> None:
        year_events = {
            "formula1": [
                _event(
                    "formula1",
                    sessions=(_session(SessionType.RACE, datetime(2026, 3, 1, 14, 0, tzinfo=UTC)),),
                )
            ]
        }
        groups = build_season_explorer(year_events, ["formula1"])
        assert len(groups) == 1
        assert groups[0].month_label == "Mars 2026"
        assert len(groups[0].rows) == 1

    def test_events_in_different_months_produce_separate_groups(self) -> None:
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
                    sessions=(_session(SessionType.RACE, datetime(2026, 4, 5, 14, 0, tzinfo=UTC)),),
                ),
            ]
        }
        groups = build_season_explorer(year_events, ["formula1"])
        assert [g.month_label for g in groups] == ["Mars 2026", "Avril 2026"]

    def test_events_in_same_month_grouped_together(self) -> None:
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
                        _session(SessionType.RACE, datetime(2026, 3, 22, 14, 0, tzinfo=UTC)),
                    ),
                ),
            ]
        }
        groups = build_season_explorer(year_events, ["formula1"])
        assert len(groups) == 1
        assert len(groups[0].rows) == 2


class TestBuildSeasonExplorerMultipleChampionships:
    def test_merges_events_from_selected_championships_into_shared_groups(self) -> None:
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
                    sessions=(_session(SessionType.RACE, datetime(2026, 3, 8, 14, 0, tzinfo=UTC)),),
                )
            ],
            "moto2": [
                _event(
                    "moto2",
                    sessions=(_session(SessionType.RACE, datetime(2026, 3, 8, 10, 0, tzinfo=UTC)),),
                )
            ],
        }
        groups = build_season_explorer(year_events, ["formula1", "motogp"])
        assert len(groups) == 1
        assert len(groups[0].rows) == 2  # moto2 not selected — excluded
        names = {row.championship_name for row in groups[0].rows}
        assert names == {"Formula 1", "MotoGP"}

    def test_unfetched_championship_in_selection_does_not_crash(self) -> None:
        year_events = {
            "formula1": [
                _event(
                    "formula1",
                    sessions=(_session(SessionType.RACE, datetime(2026, 3, 1, 14, 0, tzinfo=UTC)),),
                )
            ]
        }
        groups = build_season_explorer(year_events, ["formula1", "wec"])
        assert len(groups) == 1
        assert len(groups[0].rows) == 1


class TestBuildSeasonExplorerChronologicalOrder:
    def test_events_sorted_chronologically_regardless_of_input_order(self) -> None:
        year_events = {
            "formula1": [
                _event(
                    "formula1",
                    round_=1,
                    name="Last",
                    sessions=(
                        _session(SessionType.RACE, datetime(2026, 11, 20, 14, 0, tzinfo=UTC)),
                    ),
                ),
                _event(
                    "formula1",
                    round_=2,
                    name="First",
                    sessions=(_session(SessionType.RACE, datetime(2026, 3, 1, 14, 0, tzinfo=UTC)),),
                ),
                _event(
                    "formula1",
                    round_=3,
                    name="Middle",
                    sessions=(
                        _session(SessionType.RACE, datetime(2026, 7, 12, 14, 0, tzinfo=UTC)),
                    ),
                ),
            ]
        }
        groups = build_season_explorer(year_events, ["formula1"])
        all_names = [row.event_name for group in groups for row in group.rows]
        assert all_names == ["First Grand Prix", "Middle Grand Prix", "Last Grand Prix"]

    def test_month_groups_themselves_are_chronologically_ordered(self) -> None:
        year_events = {
            "formula1": [
                _event(
                    "formula1",
                    round_=1,
                    sessions=(_session(SessionType.RACE, datetime(2026, 9, 1, 14, 0, tzinfo=UTC)),),
                ),
                _event(
                    "formula1",
                    round_=2,
                    sessions=(_session(SessionType.RACE, datetime(2026, 2, 1, 14, 0, tzinfo=UTC)),),
                ),
                _event(
                    "formula1",
                    round_=3,
                    sessions=(_session(SessionType.RACE, datetime(2026, 5, 1, 14, 0, tzinfo=UTC)),),
                ),
            ]
        }
        groups = build_season_explorer(year_events, ["formula1"])
        assert [g.month_label for g in groups] == ["Février 2026", "Mai 2026", "Septembre 2026"]

    def test_multiple_events_same_day_sorted_by_exact_start_time(self) -> None:
        year_events = {
            "formula1": [
                _event(
                    "formula1",
                    round_=1,
                    name="Later",
                    sessions=(_session(SessionType.RACE, datetime(2026, 3, 1, 16, 0, tzinfo=UTC)),),
                ),
                _event(
                    "formula1",
                    round_=2,
                    name="Earlier",
                    sessions=(_session(SessionType.RACE, datetime(2026, 3, 1, 10, 0, tzinfo=UTC)),),
                ),
            ]
        }
        groups = build_season_explorer(year_events, ["formula1"])
        assert [row.event_name for row in groups[0].rows] == [
            "Earlier Grand Prix",
            "Later Grand Prix",
        ]

    def test_within_event_uses_earliest_session_as_sort_key(self) -> None:
        """FP1 on 30/06 then RACE on 01/07 — the event as a whole sorts by
        its earliest session, not its race."""
        year_events = {
            "formula1": [
                _event(
                    "formula1",
                    round_=1,
                    name="Spans Month Boundary",
                    sessions=(
                        _session(SessionType.FP1, datetime(2026, 6, 30, 10, 0, tzinfo=UTC)),
                        _session(SessionType.RACE, datetime(2026, 7, 1, 14, 0, tzinfo=UTC)),
                    ),
                ),
            ]
        }
        groups = build_season_explorer(year_events, ["formula1"])
        assert len(groups) == 1
        assert groups[0].month_label == "Juin 2026"


class TestBuildSeasonExplorerYearBoundary:
    def test_events_spanning_a_year_boundary_get_distinct_month_labels(self) -> None:
        """Mirrors the real Formula E anomaly (Sprint 40): a "2026" season
        can genuinely include a December 2025 round."""
        year_events = {
            "formula-e": [
                _event(
                    "formula-e",
                    round_=1,
                    sessions=(
                        _session(SessionType.RACE, datetime(2025, 12, 6, 14, 0, tzinfo=UTC)),
                    ),
                ),
                _event(
                    "formula-e",
                    round_=2,
                    sessions=(
                        _session(SessionType.RACE, datetime(2026, 1, 24, 14, 0, tzinfo=UTC)),
                    ),
                ),
            ]
        }
        groups = build_season_explorer(year_events, ["formula-e"])
        assert [g.month_label for g in groups] == ["Décembre 2025", "Janvier 2026"]


class TestSeasonMonthGroupShape:
    def test_returns_tuple_of_season_month_group(self) -> None:
        year_events = {
            "formula1": [
                _event(
                    "formula1",
                    sessions=(_session(SessionType.RACE, datetime(2026, 3, 1, 14, 0, tzinfo=UTC)),),
                )
            ]
        }
        groups = build_season_explorer(year_events, ["formula1"])
        assert isinstance(groups, tuple)
        assert isinstance(groups[0], SeasonMonthGroup)
        assert isinstance(groups[0].rows, tuple)
