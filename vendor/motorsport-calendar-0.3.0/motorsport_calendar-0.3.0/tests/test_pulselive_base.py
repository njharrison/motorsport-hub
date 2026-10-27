"""Tests for PulseliveGpSource — the shared framework for MotoGP/Moto2/Moto3.

Uses a real (trimmed, never hand-crafted) extract from Dorna's official
pulselive API, saved in tests/fixtures/real/motogp_events_2026.json — see
that directory's convention.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from motorsport_calendar.core.datasource import JsonDataSource
from motorsport_calendar.models import Championship, ChampionshipCategory, SessionType
from motorsport_calendar.providers.motogp_series.pulselive_base import (
    PulseliveGpSource,
    _classify_broadcast,
)

_FIXTURES_DIR = Path(__file__).parent / "fixtures" / "real"


def _load_fixture() -> list[dict]:
    return json.loads((_FIXTURES_DIR / "motogp_events_2026.json").read_text())


class _ConcreteSource(PulseliveGpSource):
    """Minimal concrete implementation for testing base class behaviour."""

    def __init__(self, acronym: str = "MGP", **kwargs) -> None:
        super().__init__(**kwargs)
        self._acronym = acronym

    @property
    def _series_key(self) -> str:
        return "test-series"

    @property
    def _category_acronym(self) -> str:
        return self._acronym

    @property
    def _race_duration_minutes(self) -> int:
        return 45

    def _make_championship(self, year: int) -> Championship:
        return Championship(
            id=f"test-series-{year}", name="Test Series", category=ChampionshipCategory.MOTORBIKE
        )


class TestIsJsonDataSource:
    def test_subclasses_json_data_source(self) -> None:
        assert issubclass(PulseliveGpSource, JsonDataSource)


class TestClassifyBroadcast:
    def test_practice(self) -> None:
        assert _classify_broadcast("PRACTICE", "FP1") == "practice"

    def test_unnumbered_practice(self) -> None:
        assert _classify_broadcast("PRACTICE", "PR") == "practice"

    def test_qualifying(self) -> None:
        assert _classify_broadcast("QUALIFYING", "Q1") == "qualifying"

    def test_race_sprint(self) -> None:
        assert _classify_broadcast("RACE", "SPR") == "sprint"

    def test_race_non_sprint(self) -> None:
        assert _classify_broadcast("RACE", "RAC") == "race"

    def test_press_excluded(self) -> None:
        assert _classify_broadcast("PRESS", "SHOW") is None

    def test_warm_up_excluded(self) -> None:
        assert _classify_broadcast("WARM_UP", "WUP") is None

    def test_unrecognised_kind_returns_none(self) -> None:
        assert _classify_broadcast("SOMETHING_ELSE", "X") is None


class TestParseDatetime:
    def test_normalises_positive_offset_to_utc(self) -> None:
        result = _ConcreteSource._parse_datetime("2026-02-27T10:45:00+0700")
        assert result == datetime(2026, 2, 27, 3, 45, tzinfo=UTC)

    def test_normalises_negative_offset_to_utc(self) -> None:
        result = _ConcreteSource._parse_datetime("2026-03-27T15:45:00-0500")
        assert result == datetime(2026, 3, 27, 20, 45, tzinfo=UTC)

    def test_result_has_utc_tzinfo(self) -> None:
        result = _ConcreteSource._parse_datetime("2026-02-27T10:45:00+0100")
        assert result is not None
        assert result.tzinfo is UTC

    def test_none_input_returns_none(self) -> None:
        assert _ConcreteSource._parse_datetime(None) is None

    def test_empty_string_returns_none(self) -> None:
        assert _ConcreteSource._parse_datetime("") is None

    def test_malformed_string_returns_none(self) -> None:
        assert _ConcreteSource._parse_datetime("not-a-date") is None


class TestBuildCircuit:
    def test_known_circuit_fields(self) -> None:
        event = next(e for e in _load_fixture() if e["shortname"] == "THA")
        circuit = _ConcreteSource()._build_circuit(event)
        assert circuit.name == "Chang International Circuit"
        assert circuit.country == "Thailand"
        assert circuit.timezone == "Asia/Bangkok"

    def test_empty_city_falls_back_to_circuit_name(self) -> None:
        event = next(e for e in _load_fixture() if e["shortname"] == "USA")
        circuit = _ConcreteSource()._build_circuit(event)
        assert circuit.city == circuit.name

    def test_missing_time_zone_falls_back_to_utc(self) -> None:
        circuit = _ConcreteSource()._build_circuit({"circuit": {"name": "X"}, "shortname": "X"})
        assert circuit.timezone == "UTC"

    def test_time_zone_normalised_to_iana_casing(self) -> None:
        event = next(e for e in _load_fixture() if e["shortname"] == "THA")
        circuit = _ConcreteSource()._build_circuit(event)
        assert circuit.timezone == "Asia/Bangkok"
        assert circuit.timezone != "ASIA/BANGKOK"


class TestBuildSessionsThailand:
    """MotoGP class, Thailand GP — a normal Sprint-format weekend."""

    @pytest.fixture
    def sessions(self):
        event = next(e for e in _load_fixture() if e["shortname"] == "THA")
        return _ConcreteSource("MGP")._build_sessions(event)

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
            SessionType.FP3,
            SessionType.QUALIFYING,
            SessionType.SPRINT,
            SessionType.RACE,
        }

    def test_sorted_chronologically(self, sessions) -> None:
        starts = [s.start_datetime for s in sessions]
        assert starts == sorted(starts)

    def test_all_sessions_utc(self, sessions) -> None:
        for s in sessions:
            assert s.start_datetime.tzinfo == UTC
            assert s.end_datetime.tzinfo == UTC

    def test_middle_practice_slot_carries_source_title(self, sessions) -> None:
        # The 3 PRACTICE-kind broadcasts (FP1, PR, FP2) are assigned to
        # FP1/FP2/FP3 by chronological order, not by their own label — the
        # unnumbered "Practice" (PR) falls chronologically between FP1 and
        # FP2, so it becomes our FP2 slot, and the source's own "FP2"
        # becomes our FP3 slot. Session.title still carries the real label.
        by_type = {s.type: s for s in sessions}
        assert "practice" in by_type[SessionType.FP2].title.lower()

    def test_qualifying_spans_q1_to_q2(self, sessions) -> None:
        by_type = {s.type: s for s in sessions}
        q = by_type[SessionType.QUALIFYING]
        assert q.end_datetime > q.start_datetime
        # Real end time from the source (Q2's date_end), not an invented default.
        assert q.end_datetime - q.start_datetime > timedelta(minutes=15)

    def test_race_has_default_duration(self, sessions) -> None:
        # RACE broadcasts report date_start == date_end (the source never
        # predicts a finish time) — duration falls back to the documented default.
        by_type = {s.type: s for s in sessions}
        race = by_type[SessionType.RACE]
        assert race.end_datetime - race.start_datetime == timedelta(minutes=45)

    def test_sprint_has_default_duration(self, sessions) -> None:
        by_type = {s.type: s for s in sessions}
        sprint = by_type[SessionType.SPRINT]
        assert sprint.end_datetime - sprint.start_datetime == timedelta(minutes=30)


class TestBuildSessionsMoto2Moto3:
    """Moto2/Moto3 — same event, no Sprint session (Sprint is MotoGP-only)."""

    @pytest.mark.parametrize("acronym", ["MT2", "MT3"])
    def test_five_sessions_no_sprint(self, acronym: str) -> None:
        event = next(e for e in _load_fixture() if e["shortname"] == "THA")
        sessions = _ConcreteSource(acronym)._build_sessions(event)
        types = {s.type for s in sessions}
        assert SessionType.SPRINT not in types
        assert types == {
            SessionType.FP1,
            SessionType.FP2,
            SessionType.FP3,
            SessionType.QUALIFYING,
            SessionType.RACE,
        }

    @pytest.mark.parametrize("acronym", ["MT2", "MT3"])
    def test_no_duplicate_session_types(self, acronym: str) -> None:
        event = next(e for e in _load_fixture() if e["shortname"] == "THA")
        sessions = _ConcreteSource(acronym)._build_sessions(event)
        types = [s.type for s in sessions]
        assert len(types) == len(set(types))


class TestBuildSessionsBwcCategoryIgnored:
    """USA GP has a 4th category (BWC) — must never leak into MGP/MT2/MT3."""

    def test_bwc_broadcasts_excluded_from_mgp(self) -> None:
        event = next(e for e in _load_fixture() if e["shortname"] == "USA")
        sessions = _ConcreteSource("MGP")._build_sessions(event)
        # BWC-only broadcasts must not appear as MGP sessions -- verified
        # indirectly: no duplicate/extra session types beyond the expected six.
        types = [s.type for s in sessions]
        assert len(types) == len(set(types))
        assert len(sessions) <= 6


class TestGetSeasonIntegration:
    """get_season() end-to-end with fetch_json mocked — no real network."""

    async def test_get_season_filters_to_gp_kind_only(self) -> None:
        source = _ConcreteSource("MGP", cache=None, client=MagicMock(spec=httpx.AsyncClient))
        source.fetch_json = AsyncMock(return_value=_load_fixture())  # type: ignore[method-assign]
        events = await source.get_season(2026)
        # Fixture has 5 entries: 1 TEST, 1 MEDIA, 3 GP -- only GP rounds with
        # sessions survive (TEST/MEDIA have no "circuit"/broadcasts shaped
        # like a real round and are filtered by kind before that even matters).
        assert len(events) == 3

    async def test_round_numbers_are_sequential(self) -> None:
        source = _ConcreteSource("MGP", cache=None, client=MagicMock(spec=httpx.AsyncClient))
        source.fetch_json = AsyncMock(return_value=_load_fixture())  # type: ignore[method-assign]
        events = await source.get_season(2026)
        assert [e.round for e in events] == [1, 2, 3]

    async def test_events_sorted_chronologically(self) -> None:
        source = _ConcreteSource("MGP", cache=None, client=MagicMock(spec=httpx.AsyncClient))
        source.fetch_json = AsyncMock(return_value=_load_fixture())  # type: ignore[method-assign]
        events = await source.get_season(2026)
        starts = [min(s.start_datetime for s in e.sessions) for e in events]
        assert starts == sorted(starts)

    async def test_all_uids_unique_within_a_season(self) -> None:
        source = _ConcreteSource("MGP", cache=None, client=MagicMock(spec=httpx.AsyncClient))
        source.fetch_json = AsyncMock(return_value=_load_fixture())  # type: ignore[method-assign]
        events = await source.get_season(2026)
        uids = [e.event_uid for e in events]
        assert len(uids) == len(set(uids))

    async def test_empty_events_list_returns_empty(self) -> None:
        source = _ConcreteSource("MGP", cache=None, client=MagicMock(spec=httpx.AsyncClient))
        source.fetch_json = AsyncMock(return_value=[])  # type: ignore[method-assign]
        events = await source.get_season(2026)
        assert events == []

    async def test_get_season_propagates_http_errors(self) -> None:
        source = _ConcreteSource("MGP", cache=None, client=MagicMock(spec=httpx.AsyncClient))
        request = httpx.Request("GET", "https://example.com")
        response = httpx.Response(503, request=request)
        source.fetch_json = AsyncMock(  # type: ignore[method-assign]
            side_effect=httpx.HTTPStatusError("503", request=request, response=response)
        )
        with pytest.raises(httpx.HTTPStatusError):
            await source.get_season(2026)


class TestMalformedDataResilience:
    def test_event_with_no_broadcasts_produces_no_sessions(self) -> None:
        sessions = _ConcreteSource("MGP")._build_sessions({"shortname": "X"})
        assert sessions == []

    def test_broadcast_missing_date_start_skipped(self) -> None:
        event_data = {
            "shortname": "X",
            "broadcasts": [
                {"kind": "RACE", "shortname": "RAC", "category": {"acronym": "MGP"}},
            ],
        }
        sessions = _ConcreteSource("MGP")._build_sessions(event_data)
        assert sessions == []

    def test_broadcast_wrong_category_excluded(self) -> None:
        event_data = {
            "shortname": "X",
            "broadcasts": [
                {
                    "kind": "RACE",
                    "shortname": "RAC",
                    "date_start": "2026-01-01T12:00:00+0000",
                    "date_end": "2026-01-01T12:00:00+0000",
                    "category": {"acronym": "MT3"},
                },
            ],
        }
        sessions = _ConcreteSource("MGP")._build_sessions(event_data)
        assert sessions == []

    async def test_get_season_skips_events_with_no_sessions(self) -> None:
        source = _ConcreteSource("MGP", cache=None, client=MagicMock(spec=httpx.AsyncClient))
        source.fetch_json = AsyncMock(  # type: ignore[method-assign]
            return_value=[
                {
                    "kind": "GP",
                    "id": "no-sessions",
                    "shortname": "X",
                    "date_start": "2026-01-01T00:00:00+0000",
                    "circuit": {"name": "X", "country": "X", "city": "X"},
                    "broadcasts": [],
                }
            ]
        )
        events = await source.get_season(2026)
        assert events == []
