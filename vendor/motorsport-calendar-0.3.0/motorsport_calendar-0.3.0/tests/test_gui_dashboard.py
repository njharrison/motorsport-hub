"""Tests for gui.dashboard — pure logic, no Flet, no HTTP.

Mirrors test_gui_upcoming_weekend.py's style: plain Event/Session fixtures,
no HTTP mocking needed (fetching lives in controller.get_dashboard_data).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from motorsport_calendar.gui.dashboard import NextRaceStart, build_dashboard_data
from motorsport_calendar.gui.upcoming_weekend import WeekendEntry
from motorsport_calendar.gui.update_service import UpdateCheckResult, UpdateManifest
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


def _entry(
    championship_id: str,
    *,
    name: str = "Grand Prix",
    timezone_name: str = "Europe/Paris",
    round_: int = 1,
    season: int = 2026,
    sessions: tuple[Session, ...] = (),
) -> WeekendEntry:
    """Mirrors what controller._fetch_weekend_entries produces."""
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
        timezone=timezone_name,
    )
    event = Event(
        championship=championship,
        season=season,
        round=round_,
        name=name,
        circuit=circuit,
        sessions=sessions,
        event_uid=f"{championship_id}-{round_}@test",
    )
    return WeekendEntry(championship_id=championship_id, event=event)


# A Tuesday — the upcoming weekend is Friday 2026-07-10 to Sunday 2026-07-12.
NOW = datetime(2026, 7, 7, 12, 0, tzinfo=UTC)


class TestBuildDashboardDataCounts:
    def test_total_championships_passed_through(self) -> None:
        data = build_dashboard_data([], total_championships=17, now=NOW)
        assert data.total_championships == 17

    def test_empty_entries_zero_events_and_sessions(self) -> None:
        data = build_dashboard_data([], total_championships=5, now=NOW)
        assert data.total_events_season == 0
        assert data.total_sessions_season == 0

    def test_counts_events_and_sessions_for_current_season(self) -> None:
        entries = [
            _entry(
                "formula1",
                season=2026,
                sessions=(
                    _session(SessionType.FP1, datetime(2026, 7, 10, 10, 0, tzinfo=UTC)),
                    _session(SessionType.RACE, datetime(2026, 7, 12, 14, 0, tzinfo=UTC)),
                ),
            ),
            _entry(
                "formula2",
                season=2026,
                sessions=(_session(SessionType.RACE, datetime(2026, 8, 1, 14, 0, tzinfo=UTC)),),
            ),
        ]
        data = build_dashboard_data(entries, total_championships=2, now=NOW)
        assert data.total_events_season == 2
        assert data.total_sessions_season == 3

    def test_events_from_other_seasons_excluded(self) -> None:
        entries = [
            _entry(
                "formula1",
                season=2026,
                sessions=(_session(SessionType.RACE, datetime(2026, 7, 12, 14, 0, tzinfo=UTC)),),
            ),
            _entry(
                "formula1",
                round_=2,
                season=2027,
                sessions=(_session(SessionType.RACE, datetime(2027, 1, 10, 14, 0, tzinfo=UTC)),),
            ),
        ]
        data = build_dashboard_data(entries, total_championships=1, now=NOW)
        assert data.total_events_season == 1
        assert data.total_sessions_season == 1


class TestBuildDashboardDataWeekend:
    def test_reuses_find_upcoming_weekend_when_found(self) -> None:
        entries = [
            _entry(
                "formula1",
                sessions=(_session(SessionType.RACE, datetime(2026, 7, 12, 14, 0, tzinfo=UTC)),),
            ),
        ]
        data = build_dashboard_data(entries, total_championships=1, now=NOW)
        assert data.weekend.found is True
        assert len(data.weekend.cards) == 1

    def test_weekend_not_found_when_no_entries(self) -> None:
        data = build_dashboard_data([], total_championships=0, now=NOW)
        assert data.weekend.found is False


class TestBuildDashboardDataFavorites:
    """Sprint 44 — favorite_ids is forwarded to find_upcoming_weekend as-is;
    a weekend containing a favorite shows it first among weekend.cards."""

    def test_no_favorite_ids_leaves_the_existing_order_unchanged(self) -> None:
        entries = [
            _entry(
                "wec",
                sessions=(_session(SessionType.RACE, datetime(2026, 7, 11, 8, 0, tzinfo=UTC)),),
            ),
            _entry(
                "formula1",
                sessions=(_session(SessionType.RACE, datetime(2026, 7, 12, 14, 0, tzinfo=UTC)),),
            ),
        ]
        data = build_dashboard_data(entries, total_championships=2, now=NOW)
        ids = [card.championship_id for card in data.weekend.cards]
        assert ids == ["formula1", "wec"]

    def test_favorite_championship_appears_first(self) -> None:
        entries = [
            _entry(
                "wec",
                sessions=(_session(SessionType.RACE, datetime(2026, 7, 11, 8, 0, tzinfo=UTC)),),
            ),
            _entry(
                "formula1",
                sessions=(_session(SessionType.RACE, datetime(2026, 7, 12, 14, 0, tzinfo=UTC)),),
            ),
        ]
        data = build_dashboard_data(
            entries, total_championships=2, now=NOW, favorite_ids=frozenset({"wec"})
        )
        ids = [card.championship_id for card in data.weekend.cards]
        assert ids == ["wec", "formula1"]

    def test_favorite_ids_do_not_affect_season_counts_or_next_race(self) -> None:
        """Favorites only affect weekend.cards ordering — season stats and
        "prochain départ" (out of the brief's scope) stay unaffected."""
        entries = [
            _entry(
                "formula1",
                sessions=(_session(SessionType.RACE, datetime(2026, 7, 12, 14, 0, tzinfo=UTC)),),
            ),
        ]
        without = build_dashboard_data(entries, total_championships=1, now=NOW)
        with_favorite = build_dashboard_data(
            entries, total_championships=1, now=NOW, favorite_ids=frozenset({"formula1"})
        )
        assert without.total_events_season == with_favorite.total_events_season
        assert without.total_sessions_season == with_favorite.total_sessions_season
        assert without.next_race == with_favorite.next_race


class TestBuildDashboardDataNextRace:
    def test_none_when_no_entries(self) -> None:
        data = build_dashboard_data([], total_championships=0, now=NOW)
        assert data.next_race is None

    def test_none_when_only_non_race_sessions(self) -> None:
        entries = [
            _entry(
                "formula1",
                sessions=(_session(SessionType.FP1, datetime(2026, 7, 10, 10, 0, tzinfo=UTC)),),
            ),
        ]
        data = build_dashboard_data(entries, total_championships=1, now=NOW)
        assert data.next_race is None

    def test_finds_the_next_race(self) -> None:
        entries = [
            _entry(
                "formula1",
                sessions=(_session(SessionType.RACE, datetime(2026, 7, 12, 14, 0, tzinfo=UTC)),),
            ),
        ]
        data = build_dashboard_data(entries, total_championships=1, now=NOW)
        assert data.next_race is not None
        assert isinstance(data.next_race, NextRaceStart)

    def test_ignores_past_races(self) -> None:
        entries = [
            _entry(
                "formula1",
                sessions=(_session(SessionType.RACE, datetime(2026, 7, 1, 14, 0, tzinfo=UTC)),),
            ),
        ]
        data = build_dashboard_data(entries, total_championships=1, now=NOW)
        assert data.next_race is None

    def test_picks_the_earliest_race_across_entries(self) -> None:
        entries = [
            _entry(
                "formula1",
                sessions=(_session(SessionType.RACE, datetime(2026, 7, 19, 14, 0, tzinfo=UTC)),),
            ),
            _entry(
                "formula2",
                sessions=(_session(SessionType.RACE, datetime(2026, 7, 12, 10, 0, tzinfo=UTC)),),
            ),
        ]
        data = build_dashboard_data(entries, total_championships=2, now=NOW)
        assert data.next_race is not None
        assert data.next_race.championship_name == "Formula 2"

    def test_sprint_is_not_counted_as_next_race(self) -> None:
        """Only RACE-type sessions count — Sprint is a distinct SessionType."""
        entries = [
            _entry(
                "motogp",
                sessions=(
                    _session(SessionType.SPRINT, datetime(2026, 7, 11, 14, 0, tzinfo=UTC)),
                    _session(SessionType.RACE, datetime(2026, 7, 12, 14, 0, tzinfo=UTC)),
                ),
            ),
        ]
        data = build_dashboard_data(entries, total_championships=1, now=NOW)
        assert data.next_race is not None
        # The Sprint (Saturday 11/07) would have been picked if it counted —
        # only the Race (Sunday 12/07) may appear here.
        assert "12/07" in data.next_race.display
        assert "11/07" not in data.next_race.display


# ---------------------------------------------------------------------------
# Sprint 53 — "État de Motorsport Calendar" / "Nouveautés" passthrough +
# functional_providers (the one field genuinely computed here).
# ---------------------------------------------------------------------------


class TestBuildDashboardDataStatusFields:
    def test_active_championships_passed_through(self) -> None:
        data = build_dashboard_data([], total_championships=17, now=NOW, active_championships=15)
        assert data.active_championships == 15

    def test_active_championships_defaults_to_zero(self) -> None:
        data = build_dashboard_data([], total_championships=17, now=NOW)
        assert data.active_championships == 0

    def test_favorite_count_passed_through(self) -> None:
        data = build_dashboard_data([], total_championships=17, now=NOW, favorite_count=3)
        assert data.favorite_count == 3

    def test_current_version_passed_through(self) -> None:
        data = build_dashboard_data([], total_championships=17, now=NOW, current_version="0.2.0")
        assert data.current_version == "0.2.0"

    def test_update_passed_through(self) -> None:
        update = UpdateCheckResult(update_available=True, current_version="0.2.0")
        data = build_dashboard_data([], total_championships=17, now=NOW, update=update)
        assert data.update is update

    def test_update_manifest_reachable_through_dashboard_data(self) -> None:
        manifest = UpdateManifest(
            version="0.3.0",
            release_date="2026-07-13",
            title="Motorsport Calendar 0.3.0",
            summary="Nouvelles fonctionnalités.",
            url="https://example.test/releases/0.3.0",
        )
        update = UpdateCheckResult(
            update_available=True, current_version="0.2.0", manifest=manifest
        )
        data = build_dashboard_data([], total_championships=17, now=NOW, update=update)
        assert data.update is not None
        assert data.update.manifest is manifest
        assert data.update.manifest.version == "0.3.0"

    def test_update_defaults_to_none(self) -> None:
        data = build_dashboard_data([], total_championships=17, now=NOW)
        assert data.update is None


class TestBuildDashboardDataFunctionalProviders:
    """functional_providers = distinct championship ids that actually
    contributed at least one fetched entry — never a hardcoded/config-driven
    value, always derived from what was really fetched."""

    def test_zero_when_no_entries(self) -> None:
        data = build_dashboard_data([], total_championships=17, now=NOW)
        assert data.functional_providers == 0

    def test_counts_distinct_championships(self) -> None:
        entries = [
            _entry("formula1", sessions=(_session(SessionType.RACE, NOW + timedelta(days=3)),)),
            _entry("wec", sessions=(_session(SessionType.RACE, NOW + timedelta(days=4)),)),
        ]
        data = build_dashboard_data(entries, total_championships=17, now=NOW)
        assert data.functional_providers == 2

    def test_same_championship_across_both_fetched_years_counts_once(self) -> None:
        """_fetch_weekend_entries fetches the current year AND the next
        one — a working provider contributing entries in both must not be
        double-counted."""
        entries = [
            _entry("formula1", season=2026, sessions=(_session(SessionType.RACE, NOW),)),
            _entry(
                "formula1",
                round_=2,
                season=2027,
                sessions=(_session(SessionType.RACE, NOW + timedelta(days=200)),),
            ),
        ]
        data = build_dashboard_data(entries, total_championships=17, now=NOW)
        assert data.functional_providers == 1

    def test_a_stub_that_never_contributes_an_entry_is_not_counted(self) -> None:
        """IMSA/WorldSBK-style stubs raise before ever producing a
        WeekendEntry — controller._fetch_weekend_entries already skips
        them, so they're simply absent from *entries*, exactly like any
        other championship that returned nothing."""
        entries = [
            _entry("formula1", sessions=(_session(SessionType.RACE, NOW + timedelta(days=3)),)),
        ]
        data = build_dashboard_data(entries, total_championships=17, now=NOW)
        assert data.functional_providers == 1

    def test_events_without_sessions_still_count_the_championship(self) -> None:
        """functional_providers counts *entries*, not sessions — an entry
        exists at all only because the provider successfully returned it."""
        entries = [_entry("formula1", sessions=())]
        data = build_dashboard_data(entries, total_championships=17, now=NOW)
        assert data.functional_providers == 1
