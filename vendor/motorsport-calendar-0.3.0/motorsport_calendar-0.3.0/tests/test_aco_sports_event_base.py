"""Tests for AcoSportsEventSource — the shared framework for ACO endurance series.

Uses real extracts from europeanlemansseries.com / lemanscup.com saved in
tests/fixtures/real/ (verbatim JSON-LD blocks, trimmed HTML around them —
see that directory's convention: never hand-crafted, always extracted from
the live site).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import httpx
import pytest

from motorsport_calendar.core.datasource import HtmlDataSource
from motorsport_calendar.models import Championship, ChampionshipCategory, Event, SessionType
from motorsport_calendar.providers.aco_series.sports_event_base import (
    AcoSportsEventSource,
    _session_type_for_label,
)
from tests.conftest import load_real_fixture

_CIRCUIT_DATA = {
    "Barcelona": ("Spain", "Europe/Madrid"),
    "Le Mans": ("France", "Europe/Paris"),
}


class _ConcreteSource(AcoSportsEventSource):
    """Minimal concrete implementation for testing base class behaviour."""

    @property
    def _series_key(self) -> str:
        return "test-series"

    @property
    def _base_url(self) -> str:
        return "https://example.test"

    @property
    def _event_name_prefix(self) -> str:
        return "TEST"

    @property
    def _circuit_data(self) -> dict[str, tuple[str, str]]:
        return _CIRCUIT_DATA

    def _make_championship(self, year: int) -> Championship:
        return Championship(
            id=f"test-series-{year}", name="Test Series", category=ChampionshipCategory.ENDURANCE
        )


class _ElmsLikeSource(_ConcreteSource):
    """Matches the real ELMS fixtures' event-name prefix ("ELMS")."""

    @property
    def _event_name_prefix(self) -> str:
        return "ELMS"


class _MlmcLikeSource(_ConcreteSource):
    """Matches the real MLMC fixtures' event-name prefix."""

    @property
    def _event_name_prefix(self) -> str:
        return "Michelin Le Mans Cup"


class TestIsHtmlDataSource:
    def test_subclasses_html_data_source(self) -> None:
        assert issubclass(AcoSportsEventSource, HtmlDataSource)


def _type_for(label: str) -> SessionType:
    """Unwrap ``_session_type_for_label``'s Optional result for a label known
    to match — keeps every positive test assertion below mypy-clean without
    repeating the same ``is not None`` narrowing at each call site."""
    result = _session_type_for_label(label)
    assert result is not None
    return result[0]


class TestSessionTypeForLabel:
    def test_free_practice_1(self) -> None:
        assert _type_for("Free Practice 1") == SessionType.FP1

    def test_free_practice_2(self) -> None:
        assert _type_for("Free Practice 2") == SessionType.FP2

    def test_bronze_driver_test(self) -> None:
        assert _type_for("Bronze Driver Collective Test") == SessionType.TEST

    def test_qualifying_session_variant(self) -> None:
        assert _type_for("Qualifying session LMP2") == SessionType.QUALIFYING

    def test_qualifying_dash_variant(self) -> None:
        assert _type_for("Qualifying - GT3") == SessionType.QUALIFYING

    def test_qualifying_numbered_variant(self) -> None:
        assert _type_for("Qualifying 1") == SessionType.QUALIFYING

    def test_race(self) -> None:
        assert _type_for("Race") == SessionType.RACE

    def test_race_numbered(self) -> None:
        assert _type_for("Race 1") == SessionType.RACE

    def test_unrecognised_label_returns_none(self) -> None:
        assert _session_type_for_label("Autograph Session") is None

    def test_free_practice_4(self) -> None:
        """Sprint 48 — WEC's Le Mans-only extra night session maps to the
        generic FREE_PRACTICE type, never colliding with FP3."""
        assert _type_for("Free Practice 4") == SessionType.FREE_PRACTICE

    def test_free_practice_4_does_not_match_free_practice_3(self) -> None:
        assert _type_for("Free Practice 3") == SessionType.FP3

    def test_hyperpole_bare(self) -> None:
        assert _type_for("Hyperpole") == SessionType.HYPERPOLE

    def test_hyperpole_numbered(self) -> None:
        assert _type_for("Hyperpole 1") == SessionType.HYPERPOLE
        assert _type_for("Hyperpole 2") == SessionType.HYPERPOLE

    def test_warm_up(self) -> None:
        """Sprint 48 — mapped to TEST, the closest existing SessionType;
        must never collide with Free Practice 4 (both exist on the same Le
        Mans weekend, ~37h apart)."""
        assert _type_for("Warm-up") == SessionType.TEST


class TestExtractJsonLd:
    def test_parses_elms_fixture(self) -> None:
        source = _ConcreteSource(cache=None, client=MagicMock(spec=httpx.AsyncClient))
        data = source._extract_json_ld(load_real_fixture("elms_race_barcelona.html"))
        assert data.get("@type") == "SportsEvent"
        assert "4 Hours of Barcelona" in data.get("name", "")

    def test_missing_script_returns_empty_dict(self) -> None:
        source = _ConcreteSource(cache=None, client=MagicMock(spec=httpx.AsyncClient))
        assert source._extract_json_ld("<html><body>no data here</body></html>") == {}


class TestExtractRaceUrls:
    def test_finds_race_links_in_real_snippet(self) -> None:
        source = _ConcreteSource(cache=None, client=MagicMock(spec=httpx.AsyncClient))
        urls = source._extract_race_urls(load_real_fixture("elms_season_snippet.html"), 2026)
        assert any("4-hours-of-barcelona-2026" in u for u in urls)

    def test_excludes_official_tests(self) -> None:
        source = _ConcreteSource(cache=None, client=MagicMock(spec=httpx.AsyncClient))
        urls = source._extract_race_urls(load_real_fixture("elms_season_snippet.html"), 2026)
        assert not any("official-tests" in u for u in urls)

    def test_excludes_prologue(self) -> None:
        """Sprint 48 — WEC's own pre-season test slug
        ("official-prologue-imola-2026"), never present in ELMS/MLMC."""
        source = _ConcreteSource(cache=None, client=MagicMock(spec=httpx.AsyncClient))
        html = (
            "<html><body>"
            '<a href="/en/race/official-prologue-imola-2026">Prologue</a>'
            '<a href="/en/race/6-hours-of-imola-2026">Race</a>'
            "</body></html>"
        )
        urls = source._extract_race_urls(html, 2026)
        assert not any("prologue" in u for u in urls)
        assert any("6-hours-of-imola-2026" in u for u in urls)

    def test_deduplicates_links(self) -> None:
        source = _ConcreteSource(cache=None, client=MagicMock(spec=httpx.AsyncClient))
        urls = source._extract_race_urls(load_real_fixture("elms_season_snippet.html"), 2026)
        barcelona_urls = [u for u in urls if "4-hours-of-barcelona-2026" in u]
        assert len(barcelona_urls) == 1

    def test_no_html_no_race_links_returns_empty(self) -> None:
        source = _ConcreteSource(cache=None, client=MagicMock(spec=httpx.AsyncClient))
        assert source._extract_race_urls("<html><body>nothing</body></html>", 2026) == []

    def test_race_url_belongs_to_season_is_true_by_default(self) -> None:
        """Base class default — never filters by year (ELMS/MLMC's season
        page only ever lists the current season)."""
        source = _ConcreteSource(cache=None, client=MagicMock(spec=httpx.AsyncClient))
        assert source._race_url_belongs_to_season("https://example.test/en/race/x-2099", 2026)


class TestBuildEventFromRealFixture:
    """Real ELMS Barcelona round: FP1, FP2, Bronze Driver Test, 4 qualifying
    class slots (merged), Race. Confirms live-captured behaviour, Sprint 35."""

    def _event(self) -> Event:
        source = _ElmsLikeSource(cache=None, client=MagicMock(spec=httpx.AsyncClient))
        data = source._extract_json_ld(load_real_fixture("elms_race_barcelona.html"))
        champ = source._make_championship(2026)
        return source._build_event(champ, data, round_number=1, year=2026)

    def test_event_name_strips_prefix_and_year(self) -> None:
        event = self._event()
        assert event.name == "4 Hours of Barcelona"

    def test_event_uid_format(self) -> None:
        event = self._event()
        assert event.event_uid == "test-series-2026-1@motorsport-calendar"

    def test_circuit_resolved_from_circuit_data(self) -> None:
        event = self._event()
        assert event.circuit.country == "Spain"
        assert event.circuit.timezone == "Europe/Madrid"

    def test_unknown_circuit_falls_back_gracefully(self) -> None:
        class _NoCircuitData(_ConcreteSource):
            @property
            def _circuit_data(self) -> dict[str, tuple[str, str]]:
                return {}

        source = _NoCircuitData(cache=None, client=MagicMock(spec=httpx.AsyncClient))
        data = source._extract_json_ld(load_real_fixture("elms_race_barcelona.html"))
        event = source._build_event(source._make_championship(2026), data, 1, 2026)
        assert event.circuit.country == "Unknown"
        assert event.circuit.timezone == "UTC"

    def test_five_sessions_after_qualifying_merge(self) -> None:
        """4 raw qualifying subEvents (per class) collapse into 1 Session."""
        event = self._event()
        assert len(event.sessions) == 5

    def test_session_types_present(self) -> None:
        event = self._event()
        types = {s.type for s in event.sessions}
        assert types == {
            SessionType.FP1,
            SessionType.FP2,
            SessionType.TEST,
            SessionType.QUALIFYING,
            SessionType.RACE,
        }

    def test_qualifying_spans_all_class_slots(self) -> None:
        """Fixture reports 15:05/16:20 Europe/Madrid (+02:00); _parse_datetime
        normalises to UTC (MC-002 P0-1), so 13:05/14:45 here."""
        event = self._event()
        quali = next(s for s in event.sessions if s.type == SessionType.QUALIFYING)
        assert quali.start_datetime.isoformat() == "2026-04-11T13:05:00+00:00"
        # Last class slot (LMP2, 16:20 local) + 25 min default slot length
        assert quali.end_datetime.isoformat() == "2026-04-11T14:45:00+00:00"

    def test_race_duration_from_event_end_date(self) -> None:
        """Race end derived from the event's own endDate (4h), not a guess."""
        event = self._event()
        race = next(s for s in event.sessions if s.type == SessionType.RACE)
        assert race.end_datetime - race.start_datetime == timedelta(hours=4)

    def test_no_duplicate_session_types(self) -> None:
        event = self._event()
        types = [s.type for s in event.sessions]
        assert len(types) == len(set(types))

    def test_uids_unique_within_event(self) -> None:
        event = self._event()
        uids = [f"{event.event_uid}-{s.type.value}" for s in event.sessions]
        assert len(uids) == len(set(uids))

    def test_sessions_sorted_chronologically(self) -> None:
        event = self._event()
        starts = [s.start_datetime for s in event.sessions]
        assert starts == sorted(starts)


class TestBuildEventMlmcFixture:
    def _event(self) -> Event:
        source = _MlmcLikeSource(cache=None, client=MagicMock(spec=httpx.AsyncClient))
        data = source._extract_json_ld(load_real_fixture("mlmc_race_barcelona.html"))
        champ = source._make_championship(2026)
        return source._build_event(champ, data, round_number=1, year=2026)

    def test_event_name(self) -> None:
        event = self._event()
        assert event.name == "Barcelona Round"

    def test_three_class_qualifying_merges_into_one_session(self) -> None:
        event = self._event()
        quali = [s for s in event.sessions if s.type == SessionType.QUALIFYING]
        assert len(quali) == 1

    def test_race_duration_is_two_hours(self) -> None:
        event = self._event()
        race = next(s for s in event.sessions if s.type == SessionType.RACE)
        assert race.end_datetime - race.start_datetime == timedelta(hours=2)


class TestRaceDurationSanityCap:
    """Road to Le Mans: the event's own endDate is ~61h after the race
    starts (spans the whole 24 Heures du Mans week) — must NOT be trusted
    as the race's own duration. Real bug caught during Sprint 35 live
    verification, fixed via a plausibility cap."""

    def test_rtlm_race_duration_is_capped_not_61_hours(self) -> None:
        source = _ConcreteSource(cache=None, client=MagicMock(spec=httpx.AsyncClient))
        data = source._extract_json_ld(load_real_fixture("mlmc_race_road_to_le_mans.html"))
        champ = source._make_championship(2026)
        event = source._build_event(champ, data, round_number=3, year=2026)
        race = next(s for s in event.sessions if s.type == SessionType.RACE)
        duration = race.end_datetime - race.start_datetime
        assert duration < timedelta(hours=26)
        assert duration > timedelta(minutes=0)

    def test_rtlm_uids_still_unique(self) -> None:
        source = _ConcreteSource(cache=None, client=MagicMock(spec=httpx.AsyncClient))
        data = source._extract_json_ld(load_real_fixture("mlmc_race_road_to_le_mans.html"))
        champ = source._make_championship(2026)
        event = source._build_event(champ, data, round_number=3, year=2026)
        uids = [f"{event.event_uid}-{s.type.value}" for s in event.sessions]
        assert len(uids) == len(set(uids))


class TestRaceSessionEndExtensionPoint:
    """Sprint 48 — _race_session_end() was extracted from _build_sessions()
    as an overridable hook (see OfficialWecSource) without changing the
    base class's own default behavior: trust endDate when plausible,
    return None (falls back to the generic default-duration logic)
    otherwise."""

    def test_default_uses_plausible_event_end(self) -> None:
        source = _ConcreteSource(cache=None, client=MagicMock(spec=httpx.AsyncClient))
        first_start = datetime(2026, 4, 10, 12, 0, tzinfo=UTC)
        event_end = datetime(2026, 4, 10, 16, 0, tzinfo=UTC)
        assert source._race_session_end(first_start, event_end, "4 Hours of Barcelona") == event_end

    def test_default_rejects_implausible_event_end(self) -> None:
        source = _ConcreteSource(cache=None, client=MagicMock(spec=httpx.AsyncClient))
        first_start = datetime(2026, 4, 10, 12, 0, tzinfo=UTC)
        event_end = first_start + timedelta(hours=61)  # Road to Le Mans quirk
        assert source._race_session_end(first_start, event_end, "Road to Le Mans") is None

    def test_default_returns_none_when_no_event_end(self) -> None:
        source = _ConcreteSource(cache=None, client=MagicMock(spec=httpx.AsyncClient))
        first_start = datetime(2026, 4, 10, 12, 0, tzinfo=UTC)
        assert source._race_session_end(first_start, None, "4 Hours of Barcelona") is None


class TestGetSeasonIntegration:
    """get_season() end-to-end with fetch_html mocked — no real network."""

    async def test_get_season_builds_events_from_mocked_pages(self, monkeypatch) -> None:
        source = _ConcreteSource(cache=None, client=MagicMock(spec=httpx.AsyncClient))
        season_html = load_real_fixture("elms_season_snippet.html")
        race_html = load_real_fixture("elms_race_barcelona.html")

        async def _fake_fetch_html(url: str) -> str:
            return season_html if "season" in url else race_html

        monkeypatch.setattr(source, "fetch_html", _fake_fetch_html)
        events = await source.get_season(2026)
        assert len(events) == 1
        assert events[0].round == 1

    async def test_get_season_empty_page_returns_empty_list(self, monkeypatch) -> None:
        source = _ConcreteSource(cache=None, client=MagicMock(spec=httpx.AsyncClient))

        async def _empty_fetch_html(url: str) -> str:
            return "<html><body>no races</body></html>"

        monkeypatch.setattr(source, "fetch_html", _empty_fetch_html)
        events = await source.get_season(2026)
        assert events == []

    async def test_get_season_propagates_http_errors(self, monkeypatch) -> None:
        import httpx

        source = _ConcreteSource(cache=None, client=MagicMock(spec=httpx.AsyncClient))

        async def _failing_fetch_html(url: str) -> str:
            request = httpx.Request("GET", url)
            response = httpx.Response(404, request=request)
            raise httpx.HTTPStatusError("404", request=request, response=response)

        monkeypatch.setattr(source, "fetch_html", _failing_fetch_html)
        with pytest.raises(httpx.HTTPStatusError):
            await source.get_season(2026)


class TestParseDatetimeEdgeCases:
    def test_none_returns_none(self) -> None:
        source = _ConcreteSource(cache=None, client=MagicMock(spec=httpx.AsyncClient))
        assert source._parse_datetime(None) is None

    def test_empty_string_returns_none(self) -> None:
        source = _ConcreteSource(cache=None, client=MagicMock(spec=httpx.AsyncClient))
        assert source._parse_datetime("") is None

    def test_malformed_string_returns_none(self) -> None:
        source = _ConcreteSource(cache=None, client=MagicMock(spec=httpx.AsyncClient))
        assert source._parse_datetime("not-a-date") is None

    def test_valid_iso_string_parses(self) -> None:
        source = _ConcreteSource(cache=None, client=MagicMock(spec=httpx.AsyncClient))
        result = source._parse_datetime("2026-04-10T11:50:00+02:00")
        assert result is not None
        assert result.year == 2026

    def test_local_offset_normalised_to_utc(self) -> None:
        """MC-002 P0-1 regression guard: the JSON-LD's local fixed offset
        (e.g. +02:00) must never reach IcsExporter as-is — it would produce
        a synthetic, non-IANA TZID with no VTIMEZONE block (invalid RFC
        5545). _parse_datetime must always return a UTC-aware datetime."""
        source = _ConcreteSource(cache=None, client=MagicMock(spec=httpx.AsyncClient))
        result = source._parse_datetime("2026-04-10T14:50:00+02:00")
        assert result is not None
        assert result.tzinfo == UTC
        assert result.utcoffset() == timedelta(0)
        assert result.hour == 12
        assert result.minute == 50


class TestMalformedDataResilience:
    """Neither a broken page nor an unrecognised session should crash the
    scraper — matches the project's established "graceful, never crash on
    unexpected upstream data" convention."""

    def test_malformed_json_ld_returns_empty_dict(self) -> None:
        source = _ConcreteSource(cache=None, client=MagicMock(spec=httpx.AsyncClient))
        html = (
            '<html><head><script type="application/ld+json">{not valid json</script></head></html>'
        )
        assert source._extract_json_ld(html) == {}

    def test_subevent_missing_start_date_is_skipped(self) -> None:
        source = _ConcreteSource(cache=None, client=MagicMock(spec=httpx.AsyncClient))
        data = {
            "name": "TEST Event 2026",
            "location": {"name": "Barcelona"},
            "subEvent": [{"name": "Free Practice 1 - Event"}],  # no startDate
        }
        event = source._build_event(source._make_championship(2026), data, 1, 2026)
        assert event.sessions == ()

    def test_unrecognised_session_label_is_skipped(self) -> None:
        source = _ConcreteSource(cache=None, client=MagicMock(spec=httpx.AsyncClient))
        data = {
            "name": "TEST Event 2026",
            "location": {"name": "Barcelona"},
            "subEvent": [
                {"name": "Autograph Session - Event", "startDate": "2026-04-10T10:00:00+02:00"}
            ],
        }
        event = source._build_event(source._make_championship(2026), data, 1, 2026)
        assert event.sessions == ()

    def test_absolute_href_used_as_is(self) -> None:
        source = _ConcreteSource(cache=None, client=MagicMock(spec=httpx.AsyncClient))
        html = (
            '<html><body><a href="https://other.test/en/race/some-race-2026">Race</a></body></html>'
        )
        urls = source._extract_race_urls(html, 2026)
        assert urls == ["https://other.test/en/race/some-race-2026"]
