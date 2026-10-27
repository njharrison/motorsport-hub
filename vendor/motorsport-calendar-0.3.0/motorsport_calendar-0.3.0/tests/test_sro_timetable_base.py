"""Tests for SroTimetableSource — the shared framework for SRO GT series.

Uses real extracts from the four SRO Motorsports Group sites
(gt-world-challenge-{europe,america,asia}.com, intercontinentalgtchallenge.com)
saved in tests/fixtures/real/ — trimmed HTML around the real title/heading/
timetable markup, never hand-crafted (see that directory's convention).
"""

from __future__ import annotations

from datetime import date, time, timedelta
from unittest.mock import MagicMock

from bs4 import BeautifulSoup
import httpx
import pytest

from motorsport_calendar.core.datasource import HtmlDataSource
from motorsport_calendar.models import Championship, ChampionshipCategory, SessionType
from motorsport_calendar.providers.sro_series.timetable_base import (
    SroTimetableSource,
    _classify_label,
    _parse_time_of_day,
    _resolve_utc_datetime,
)
from tests.conftest import load_real_fixture


class _ConcreteSource(SroTimetableSource):
    """Minimal concrete implementation for testing base class behaviour."""

    @property
    def _series_key(self) -> str:
        return "test-series"

    @property
    def _base_url(self) -> str:
        return "https://example.test"

    def _make_championship(self, year: int) -> Championship:
        return Championship(
            id=f"test-series-{year}", name="Test Series", category=ChampionshipCategory.GT
        )


class TestIsHtmlDataSource:
    def test_subclasses_html_data_source(self) -> None:
        assert issubclass(SroTimetableSource, HtmlDataSource)


class TestClassifyLabel:
    def test_race_plain(self) -> None:
        assert _classify_label("Race") == "race"

    def test_race_numbered(self) -> None:
        assert _classify_label("Race 2") == "race"

    def test_main_race(self) -> None:
        assert _classify_label("Main Race") == "race"

    def test_qualifying_plain(self) -> None:
        assert _classify_label("Qualifying 1") == "qualifying"

    def test_qualifying_with_group_suffix(self) -> None:
        assert _classify_label("Qualifying 1 - Group A") == "qualifying"

    def test_qualifying_combined(self) -> None:
        assert _classify_label("Qualifying Combined") == "qualifying"

    def test_free_practice(self) -> None:
        assert _classify_label("Free Practice 1") == "practice"

    def test_practice_with_bronze_suffix(self) -> None:
        assert _classify_label("Free Practice 2 (Bronze Drivers)") == "practice"

    def test_night_practice(self) -> None:
        assert _classify_label("Night Practice") == "practice"

    def test_bronze_session(self) -> None:
        assert _classify_label("Bronze Session") == "practice"

    def test_superpole(self) -> None:
        assert _classify_label("Superpole") == "superpole"

    def test_test_session_excluded(self) -> None:
        assert _classify_label("Official Paid Test Session 1") is None

    def test_bronze_test_excluded(self) -> None:
        assert _classify_label("Bronze Test") is None

    def test_parade_excluded(self) -> None:
        assert _classify_label("Spa Parade") is None

    def test_pit_walk_excluded(self) -> None:
        assert _classify_label("Pit Walk") is None

    def test_warm_up_excluded(self) -> None:
        assert _classify_label("Warm-up") is None

    def test_pre_qualifying_excluded(self) -> None:
        assert _classify_label("Pre-Qualifying") is None

    def test_unrecognised_label_returns_none(self) -> None:
        assert _classify_label("Autograph Session") is None


class TestParseTimeOfDay:
    def test_24h_format(self) -> None:
        assert _parse_time_of_day("22:45") == time(22, 45)

    def test_12h_am_format(self) -> None:
        assert _parse_time_of_day("09:35 am") == time(9, 35)

    def test_12h_pm_format(self) -> None:
        assert _parse_time_of_day("02:35 pm") == time(14, 35)

    def test_invalid_text_returns_none(self) -> None:
        assert _parse_time_of_day("TBC") is None

    def test_empty_text_returns_none(self) -> None:
        assert _parse_time_of_day("") is None


class TestResolveUtcDatetime:
    def test_negative_offset_same_day(self) -> None:
        # Chicago (COTA), UTC-5: local 09:35am, GMT 02:35pm -> same calendar day.
        result = _resolve_utc_datetime(date(2026, 4, 24), "09:35 am", "02:35 pm")
        assert result is not None
        assert result.isoformat() == "2026-04-24T14:35:00+00:00"

    def test_positive_offset_rolls_back_a_day(self) -> None:
        # Sydney (Bathurst), UTC+11ish: local Friday 08:45 is Thursday 22:45 UTC.
        result = _resolve_utc_datetime(date(2026, 2, 13), "08:45", "22:45")
        assert result is not None
        assert result.isoformat() == "2026-02-12T22:45:00+00:00"

    def test_unparseable_local_time_returns_none(self) -> None:
        assert _resolve_utc_datetime(date(2026, 2, 13), "TBC", "22:45") is None

    def test_unparseable_gmt_time_returns_none(self) -> None:
        assert _resolve_utc_datetime(date(2026, 2, 13), "08:45", "TBC") is None


class TestExtractRoundUrls:
    def test_gtwc_europe_ten_rounds_in_order(self) -> None:
        class Src(_ConcreteSource):
            @property
            def _base_url(self) -> str:
                return "https://www.gt-world-challenge-europe.com"

        urls = Src()._extract_round_urls(load_real_fixture("gtwc_europe_calendar.html"))
        assert len(urls) == 10
        assert urls[0].endswith("/event/246/circuit-paul-ricard")
        assert urls[-1].endswith("/event/255/portimao")

    def test_gtwc_america_seven_rounds_chronological_despite_dom_order(self) -> None:
        class Src(_ConcreteSource):
            @property
            def _base_url(self) -> str:
                return "https://www.gt-world-challenge-america.com"

        urls = Src()._extract_round_urls(load_real_fixture("gtwc_america_calendar.html"))
        assert len(urls) == 7
        # Round 1 (Sonoma) appears after Round 5-7 in the raw DOM (past-events
        # block renders after the upcoming grid) — extraction must still sort
        # by the parsed round number, not DOM order.
        assert urls[0].endswith("/event/111/sonoma-raceway")
        assert urls[-1].endswith("/event/117/indianpolis-8-hour")

    def test_gtwc_asia_six_venues_from_round_pair_labels(self) -> None:
        class Src(_ConcreteSource):
            @property
            def _base_url(self) -> str:
                return "https://www.gt-world-challenge-asia.com"

        # Asia labels rounds "Round N & M" (one venue = one double-header
        # weekend) — extraction must still resolve one URL per venue.
        urls = Src()._extract_round_urls(load_real_fixture("gtwc_asia_calendar.html"))
        assert len(urls) == 6
        assert urls[0].endswith("/event/80/sepang")
        assert urls[-1].endswith("/event/90/shanghai-international-circuit")

    def test_igtc_five_rounds_including_malformed_href(self) -> None:
        class Src(_ConcreteSource):
            @property
            def _base_url(self) -> str:
                return "https://www.intercontinentalgtchallenge.com"

        urls = Src()._extract_round_urls(load_real_fixture("igtc_calendar.html"))
        assert len(urls) == 5
        # The site's own href for this round contains a raw space and mixed
        # case ("/event/153/Indianapolis 8 Hour") — must come back URL-safe.
        assert " " not in urls[-1]
        assert "%20" in urls[-1]

    def test_no_round_labels_returns_empty(self) -> None:
        src = _ConcreteSource()
        assert src._extract_round_urls("<html><body>nothing here</body></html>") == []


class TestBuildSessionsSprintCupFormat:
    """GT World Challenge Europe, Misano — a two-race "Sprint Cup" weekend."""

    @pytest.fixture
    def sessions(self):
        soup = BeautifulSoup(load_real_fixture("gtwc_europe_event_misano.html"), "lxml")
        return _ConcreteSource()._build_sessions(soup, "https://x.com/event/250/misano", 2026)

    def test_six_sessions(self, sessions) -> None:
        assert len(sessions) == 6

    def test_no_duplicate_session_types(self, sessions) -> None:
        types = [s.type for s in sessions]
        assert len(types) == len(set(types))

    def test_session_types_present(self, sessions) -> None:
        types = {s.type for s in sessions}
        assert types == {
            SessionType.FP1,
            SessionType.FP2,
            SessionType.SPRINT_QUALIFYING,
            SessionType.SPRINT,
            SessionType.QUALIFYING,
            SessionType.RACE,
        }

    def test_sorted_chronologically(self, sessions) -> None:
        starts = [s.start_datetime for s in sessions]
        assert starts == sorted(starts)

    def test_sprint_precedes_race(self, sessions) -> None:
        by_type = {s.type: s for s in sessions}
        assert by_type[SessionType.SPRINT].start_datetime < by_type[SessionType.RACE].start_datetime

    def test_race_default_duration_no_hour_slug(self, sessions) -> None:
        by_type = {s.type: s for s in sessions}
        race = by_type[SessionType.RACE]
        assert race.end_datetime - race.start_datetime == timedelta(minutes=90)


class TestBuildSessionsEnduranceFormat:
    """GT World Challenge Europe, CrowdStrike 24 Hours of Spa — single-race endurance."""

    @pytest.fixture
    def sessions(self):
        soup = BeautifulSoup(load_real_fixture("gtwc_europe_event_spa24h.html"), "lxml")
        return _ConcreteSource()._build_sessions(
            soup, "https://x.com/event/249/crowdstrike-24-hours-of-spa", 2026
        )

    def test_no_duplicate_session_types(self, sessions) -> None:
        types = [s.type for s in sessions]
        assert len(types) == len(set(types))

    def test_session_types_present(self, sessions) -> None:
        types = {s.type for s in sessions}
        assert types == {
            SessionType.FP1,
            SessionType.FP2,
            SessionType.FP3,
            SessionType.QUALIFYING,
            SessionType.HYPERPOLE,
            SessionType.RACE,
        }

    def test_multi_slot_qualifying_merged_into_one_session(self, sessions) -> None:
        # Source has Qualifying 1/2/3/4 + Qualifying Combined = 5 rows.
        by_type = {s.type: s for s in sessions}
        assert by_type[SessionType.QUALIFYING] is not None

    def test_night_practice_becomes_fp3(self, sessions) -> None:
        by_type = {s.type: s for s in sessions}
        assert by_type[SessionType.FP3].title == "Night Practice"

    def test_superpole_maps_to_hyperpole(self, sessions) -> None:
        by_type = {s.type: s for s in sessions}
        assert by_type[SessionType.HYPERPOLE].title == "Superpole"

    def test_race_duration_from_hour_slug(self, sessions) -> None:
        by_type = {s.type: s for s in sessions}
        race = by_type[SessionType.RACE]
        assert race.end_datetime - race.start_datetime == timedelta(hours=24)

    def test_parade_and_pit_walk_excluded(self, sessions) -> None:
        titles = [s.title for s in sessions]
        assert "Spa Parade" not in titles
        assert "Pit Walk" not in titles


class TestBuildSessionsPracticeOverflow:
    """Bathurst 12 Hour — six numbered Free Practice sessions, only 3 FP slots exist."""

    @pytest.fixture
    def sessions(self):
        soup = BeautifulSoup(load_real_fixture("igtc_event_bathurst.html"), "lxml")
        return _ConcreteSource()._build_sessions(
            soup, "https://x.com/event/149/bathurst-12-hour", 2026
        )

    def test_no_duplicate_session_types(self, sessions) -> None:
        types = [s.type for s in sessions]
        assert len(types) == len(set(types))

    def test_fp3_merges_the_overflow(self, sessions) -> None:
        by_type = {s.type: s for s in sessions}
        fp1, fp3 = by_type[SessionType.FP1], by_type[SessionType.FP3]
        assert fp1.title == "Free Practice 1"
        # FP3 absorbs everything from the 3rd practice session onward
        # (Free Practice 3/4/5/6) — its span must cover the last one.
        assert fp3.end_datetime > fp3.start_datetime + timedelta(hours=1)

    def test_race_duration_from_hour_slug(self, sessions) -> None:
        by_type = {s.type: s for s in sessions}
        race = by_type[SessionType.RACE]
        assert race.end_datetime - race.start_datetime == timedelta(hours=12)

    def test_single_race_no_relabelling(self, sessions) -> None:
        types = {s.type for s in sessions}
        assert SessionType.SPRINT not in types
        assert SessionType.SPRINT_QUALIFYING not in types


class TestBuildSessionsGtwcAmericaFormat:
    """GT World Challenge America, COTA — single race, 12h AM/PM local time column."""

    @pytest.fixture
    def sessions(self):
        soup = BeautifulSoup(load_real_fixture("gtwc_america_event_cota.html"), "lxml")
        return _ConcreteSource()._build_sessions(
            soup, "https://x.com/event/112/circuit-of-the-americas", 2026
        )

    def test_five_sessions(self, sessions) -> None:
        assert len(sessions) == 5

    def test_test_session_excluded(self, sessions) -> None:
        titles = [s.title for s in sessions]
        assert "Test Session" not in titles

    def test_no_duplicate_session_types(self, sessions) -> None:
        types = [s.type for s in sessions]
        assert len(types) == len(set(types))

    def test_qualifying_combined_maps_to_qualifying(self, sessions) -> None:
        by_type = {s.type: s for s in sessions}
        assert by_type[SessionType.QUALIFYING].title == "Qualifying Combined"


class TestBuildSessionsGtwcAsiaFormat:
    """GT World Challenge Asia, Sepang — sprint-cup double-header via a different site."""

    @pytest.fixture
    def sessions(self):
        soup = BeautifulSoup(load_real_fixture("gtwc_asia_event_sepang.html"), "lxml")
        return _ConcreteSource()._build_sessions(soup, "https://x.com/event/80/sepang", 2026)

    def test_no_duplicate_session_types(self, sessions) -> None:
        types = [s.type for s in sessions]
        assert len(types) == len(set(types))

    def test_two_race_slots_relabelled(self, sessions) -> None:
        # Sepang's grid for Race 2 is set from Race 1's result (no separate
        # qualifying block precedes it) — both "Qualifying 1"/"Qualifying 2"
        # entries land before Race 1 and merge into SPRINT_QUALIFYING only.
        types = {s.type for s in sessions}
        assert SessionType.SPRINT in types
        assert SessionType.RACE in types
        assert SessionType.SPRINT_QUALIFYING in types


class TestBuildCircuit:
    def test_known_slug_uses_lookup_table(self) -> None:
        soup = BeautifulSoup(load_real_fixture("gtwc_europe_event_misano.html"), "lxml")
        circuit = _ConcreteSource()._build_circuit(soup, "misano")
        assert circuit.name == "Misano World Circuit"
        assert circuit.timezone == "Europe/Rome"
        assert circuit.country == "Italy"

    def test_unknown_slug_falls_back_to_heading_and_utc(self) -> None:
        soup = BeautifulSoup(load_real_fixture("gtwc_europe_event_misano.html"), "lxml")
        circuit = _ConcreteSource()._build_circuit(soup, "totally-unmapped-slug")
        assert circuit.name == "Misano"  # feature__heading text
        assert circuit.timezone == "UTC"

    def test_city_equals_name(self) -> None:
        soup = BeautifulSoup(load_real_fixture("gtwc_europe_event_misano.html"), "lxml")
        circuit = _ConcreteSource()._build_circuit(soup, "misano")
        assert circuit.city == circuit.name


class TestExtractCountry:
    def test_country_from_title(self) -> None:
        soup = BeautifulSoup(load_real_fixture("gtwc_america_event_cota.html"), "lxml")
        assert _ConcreteSource()._extract_country(soup) == "United States of America"

    def test_missing_title_returns_unknown(self) -> None:
        soup = BeautifulSoup("<html><body>no title</body></html>", "lxml")
        assert _ConcreteSource()._extract_country(soup) == "Unknown"


class TestInferRaceDuration:
    def test_twelve_hour_slug(self) -> None:
        assert _ConcreteSource()._infer_race_duration("bathurst-12-hour") == timedelta(hours=12)

    def test_twenty_four_hours_slug(self) -> None:
        duration = _ConcreteSource()._infer_race_duration("crowdstrike-24-hours-of-spa")
        assert duration == timedelta(hours=24)

    def test_no_hour_pattern_uses_default(self) -> None:
        assert _ConcreteSource()._infer_race_duration("circuit-of-the-americas") == timedelta(
            minutes=90
        )

    def test_distance_only_slug_uses_default(self) -> None:
        # "1000km" has no "hour" digit — accepted approximation (see module
        # docstring), not fabricated from real distance/speed data.
        assert _ConcreteSource()._infer_race_duration("suzuka-1000km") == timedelta(minutes=90)


class TestGetSeasonIntegration:
    """get_season() end-to-end with fetch_html mocked — no real network."""

    async def test_get_season_builds_events_from_mocked_pages(self) -> None:
        source = _ConcreteSource(cache=None, client=MagicMock(spec=httpx.AsyncClient))
        calendar_html = load_real_fixture("gtwc_europe_calendar.html")
        event_html = load_real_fixture("gtwc_europe_event_misano.html")

        async def _fake_fetch_html(url: str) -> str:
            return calendar_html if url.endswith("/calendar") else event_html

        source.fetch_html = _fake_fetch_html  # type: ignore[method-assign]
        events = await source.get_season(2026)
        # All 10 rounds resolve to the same fixture (Misano) in this test —
        # what matters is round numbering and that every event survives.
        assert len(events) == 10
        assert [e.round for e in events] == list(range(1, 11))

    async def test_get_season_skips_events_with_no_published_timetable(self) -> None:
        source = _ConcreteSource(cache=None, client=MagicMock(spec=httpx.AsyncClient))
        calendar_html = load_real_fixture("gtwc_europe_calendar.html")

        async def _fake_fetch_html(url: str) -> str:
            if url.endswith("/calendar"):
                return calendar_html
            return "<html><head><title>X, Y, Z</title></head><body></body></html>"

        source.fetch_html = _fake_fetch_html  # type: ignore[method-assign]
        events = await source.get_season(2026)
        assert events == []

    async def test_get_season_empty_calendar_returns_empty_list(self) -> None:
        source = _ConcreteSource(cache=None, client=MagicMock(spec=httpx.AsyncClient))

        async def _empty_fetch_html(url: str) -> str:
            return "<html><body>no rounds</body></html>"

        source.fetch_html = _empty_fetch_html  # type: ignore[method-assign]
        events = await source.get_season(2026)
        assert events == []

    async def test_get_season_propagates_http_errors(self) -> None:
        source = _ConcreteSource(cache=None, client=MagicMock(spec=httpx.AsyncClient))

        async def _failing_fetch_html(url: str) -> str:
            request = httpx.Request("GET", url)
            response = httpx.Response(503, request=request)
            raise httpx.HTTPStatusError("503", request=request, response=response)

        source.fetch_html = _failing_fetch_html  # type: ignore[method-assign]
        with pytest.raises(httpx.HTTPStatusError):
            await source.get_season(2026)

    async def test_all_uids_unique_within_a_season(self) -> None:
        source = _ConcreteSource(cache=None, client=MagicMock(spec=httpx.AsyncClient))
        calendar_html = load_real_fixture("gtwc_europe_calendar.html")
        event_htmls = [
            load_real_fixture("gtwc_europe_event_misano.html"),
            load_real_fixture("gtwc_europe_event_spa24h.html"),
        ]

        async def _fake_fetch_html(url: str) -> str:
            if url.endswith("/calendar"):
                return calendar_html
            # Alternate between the two fixtures so different rounds have
            # genuinely different slugs (and thus different event_uid).
            index = hash(url) % 2
            return event_htmls[index]

        source.fetch_html = _fake_fetch_html  # type: ignore[method-assign]
        events = await source.get_season(2026)
        uids = [e.event_uid for e in events]
        assert len(uids) == len(set(uids))


class TestMalformedDataResilience:
    def test_missing_caption_row_skipped(self) -> None:
        html = """
        <html><body>
        <div class="timetable__container">
          <div class="timetable__table-body">
            <tr><td>Race</td><td>10:00</td><td>10:00</td></tr>
          </div>
        </div>
        </body></html>
        """
        soup = BeautifulSoup(html, "lxml")
        assert _ConcreteSource()._extract_raw_entries(soup, 2026) == []

    def test_malformed_caption_date_skipped(self) -> None:
        html = """
        <html><body>
        <div class="timetable__container">
          <caption class="timetable__caption"><span>Not a real date</span></caption>
          <div class="timetable__table-body">
            <tr><td>Race</td><td>10:00</td><td>10:00</td></tr>
          </div>
        </div>
        </body></html>
        """
        soup = BeautifulSoup(html, "lxml")
        assert _ConcreteSource()._extract_raw_entries(soup, 2026) == []

    def test_row_with_too_few_cells_skipped(self) -> None:
        html = """
        <html><body>
        <div class="timetable__container">
          <caption class="timetable__caption"><span>Friday, 24 April</span></caption>
          <div class="timetable__table-body">
            <tr><td>Race</td><td>10:00</td></tr>
          </div>
        </div>
        </body></html>
        """
        soup = BeautifulSoup(html, "lxml")
        assert _ConcreteSource()._extract_raw_entries(soup, 2026) == []

    def test_no_sessions_no_race_returns_empty(self) -> None:
        html = """
        <html><head><title>X, Y, Z</title></head><body>
        <div class="timetable__container">
          <caption class="timetable__caption"><span>Friday, 24 April</span></caption>
          <div class="timetable__table-body">
            <tr><td>Free Practice 1</td><td>10:00</td><td>10:00</td></tr>
          </div>
        </div>
        </body></html>
        """
        soup = BeautifulSoup(html, "lxml")
        # Practice-only day, no Race entry at all -> _build_sessions bails.
        assert _ConcreteSource()._build_sessions(soup, "https://x.com/event/1/x", 2026) == []
