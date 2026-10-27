"""Tests for JolpicaSource — all HTTP calls are mocked."""

from __future__ import annotations

from datetime import timedelta
from typing import Any
from unittest.mock import MagicMock

import httpx
import pytest

from motorsport_calendar.models import ChampionshipCategory, SessionType
from motorsport_calendar.providers.formula1.sources.jolpica import (
    JolpicaSource,
    _build_circuit,
    _build_event,
    _build_session,
    _make_championship,
    _resolve_timezone,
)

# ---------------------------------------------------------------------------
# Fixtures — realistic Jolpica API payloads
# ---------------------------------------------------------------------------

_BAHRAIN_RACE: dict[str, Any] = {
    "season": "2024",
    "round": "1",
    "raceName": "Bahrain Grand Prix",
    "Circuit": {
        "circuitId": "bahrain",
        "circuitName": "Bahrain International Circuit",
        "Location": {"locality": "Sakhir", "country": "Bahrain"},
    },
    "date": "2024-03-02",
    "time": "15:00:00Z",
    "FirstPractice": {"date": "2024-02-29", "time": "11:30:00Z"},
    "SecondPractice": {"date": "2024-02-29", "time": "15:00:00Z"},
    "ThirdPractice": {"date": "2024-03-01", "time": "11:30:00Z"},
    "Qualifying": {"date": "2024-03-01", "time": "15:00:00Z"},
}

_AUSTRALIA_RACE: dict[str, Any] = {
    "season": "2024",
    "round": "3",
    "raceName": "Australian Grand Prix",
    "Circuit": {
        "circuitId": "albert_park",
        "circuitName": "Albert Park Grand Prix Circuit",
        "Location": {"locality": "Melbourne", "country": "Australia"},
    },
    "date": "2024-03-24",
    "time": "04:00:00Z",
    "FirstPractice": {"date": "2024-03-22", "time": "01:30:00Z"},
    "SecondPractice": {"date": "2024-03-22", "time": "05:00:00Z"},
    "ThirdPractice": {"date": "2024-03-23", "time": "01:30:00Z"},
    "Qualifying": {"date": "2024-03-23", "time": "05:00:00Z"},
}

# Sprint weekend: FP1 + Sprint Qualifying + Sprint + Qualifying + Race
_CHINA_SPRINT_RACE: dict[str, Any] = {
    "season": "2024",
    "round": "5",
    "raceName": "Chinese Grand Prix",
    "Circuit": {
        "circuitId": "shanghai",
        "circuitName": "Shanghai International Circuit",
        "Location": {"locality": "Shanghai", "country": "China"},
    },
    "date": "2024-04-21",
    "time": "07:00:00Z",
    "FirstPractice": {"date": "2024-04-19", "time": "03:30:00Z"},
    "Qualifying": {"date": "2024-04-19", "time": "07:00:00Z"},
    "SprintQualifying": {"date": "2024-04-20", "time": "03:30:00Z"},
    "Sprint": {"date": "2024-04-20", "time": "07:00:00Z"},
}

# Historical race without session times (pre-2000 style)
_HISTORICAL_RACE: dict[str, Any] = {
    "season": "1950",
    "round": "1",
    "raceName": "British Grand Prix",
    "Circuit": {
        "circuitId": "silverstone",
        "circuitName": "Silverstone Circuit",
        "Location": {"locality": "Silverstone", "country": "UK"},
    },
    "date": "1950-05-13",
    # no "time" field, no session fields
}


# ---------------------------------------------------------------------------
# Mock client factory
# ---------------------------------------------------------------------------


def _make_client(races: list[dict]) -> MagicMock:
    """Return a fake httpx.AsyncClient that serves a Jolpica-style response."""

    async def get(path: str, *, params: dict | None = None) -> MagicMock:
        resp = MagicMock(spec=httpx.Response)
        resp.raise_for_status.return_value = None
        resp.json.return_value = {
            "MRData": {
                "RaceTable": {
                    "season": "2024",
                    "Races": races,
                }
            }
        }
        return resp

    client = MagicMock(spec=httpx.AsyncClient)
    client.get = get
    return client


def _make_error_client(status_code: int) -> MagicMock:
    """Return a fake client whose get() raises HTTPStatusError."""

    async def get(path: str, *, params: dict | None = None) -> MagicMock:
        request = httpx.Request("GET", f"http://api.jolpi.ca/ergast/f1{path}")
        response = httpx.Response(status_code, request=request)
        raise httpx.HTTPStatusError(
            message=f"HTTP {status_code}",
            request=request,
            response=response,
        )

    client = MagicMock(spec=httpx.AsyncClient)
    client.get = get
    return client


def _make_timeout_client() -> MagicMock:
    """Return a fake client whose get() raises TimeoutException."""

    async def get(path: str, *, params: dict | None = None) -> MagicMock:
        raise httpx.TimeoutException("Request timed out")

    client = MagicMock(spec=httpx.AsyncClient)
    client.get = get
    return client


# ---------------------------------------------------------------------------
# TestResolveTimezone
# ---------------------------------------------------------------------------


class TestResolveTimezone:
    def test_known_circuit_ids_return_iana_timezones(self) -> None:
        assert _resolve_timezone("bahrain") == "Asia/Bahrain"
        assert _resolve_timezone("albert_park") == "Australia/Melbourne"
        assert _resolve_timezone("monaco") == "Europe/Monaco"
        assert _resolve_timezone("silverstone") == "Europe/London"
        assert _resolve_timezone("shanghai") == "Asia/Shanghai"

    def test_unknown_circuit_id_returns_utc(self) -> None:
        assert _resolve_timezone("unknown_circuit") == "UTC"
        assert _resolve_timezone("") == "UTC"


# ---------------------------------------------------------------------------
# TestBuildCircuit
# ---------------------------------------------------------------------------


class TestBuildCircuit:
    def test_fields_mapped_correctly(self) -> None:
        circuit = _build_circuit(_BAHRAIN_RACE)
        assert circuit.id == "jolpica-bahrain"
        assert circuit.name == "Bahrain International Circuit"
        assert circuit.city == "Sakhir"
        assert circuit.country == "Bahrain"
        assert circuit.timezone == "Asia/Bahrain"

    def test_unknown_circuit_gets_utc_timezone(self) -> None:
        race = {
            **_BAHRAIN_RACE,
            "Circuit": {
                "circuitId": "nowhere",
                "circuitName": "Nowhere GP",
                "Location": {"locality": "Nowhere", "country": "Neverland"},
            },
        }
        circuit = _build_circuit(race)
        assert circuit.timezone == "UTC"

    def test_circuit_id_prefixed_with_jolpica(self) -> None:
        circuit = _build_circuit(_AUSTRALIA_RACE)
        assert circuit.id == "jolpica-albert_park"


# ---------------------------------------------------------------------------
# TestBuildSession
# ---------------------------------------------------------------------------


class TestBuildSession:
    def test_complete_session_is_built(self) -> None:
        data = {"date": "2024-03-02", "time": "15:00:00Z"}
        session = _build_session(data, SessionType.RACE, 130)
        assert session is not None
        assert session.type == SessionType.RACE
        assert session.title == "Race"
        assert session.start_datetime.tzinfo is not None
        assert session.end_datetime.tzinfo is not None

    def test_missing_date_returns_none(self) -> None:
        data: dict[str, str | None] = {"date": None, "time": "15:00:00Z"}
        assert _build_session(data, SessionType.RACE, 130) is None

    def test_missing_time_returns_none(self) -> None:
        data: dict[str, str | None] = {"date": "2024-03-02", "time": None}
        assert _build_session(data, SessionType.RACE, 130) is None

    def test_invalid_datetime_returns_none(self) -> None:
        data = {"date": "not-a-date", "time": "15:00:00Z"}
        assert _build_session(data, SessionType.RACE, 130) is None

    def test_naive_datetime_returns_none(self) -> None:
        # Time without Z suffix → naive datetime
        data = {"date": "2024-03-02", "time": "15:00:00"}
        assert _build_session(data, SessionType.RACE, 130) is None

    def test_end_datetime_inferred_from_duration(self) -> None:
        data = {"date": "2024-03-02", "time": "15:00:00Z"}
        session = _build_session(data, SessionType.FP1, 60)
        assert session is not None
        assert session.end_datetime == session.start_datetime + timedelta(minutes=60)

    def test_sprint_qualifying_duration_is_45_minutes(self) -> None:
        data = {"date": "2024-04-20", "time": "03:30:00Z"}
        session = _build_session(data, SessionType.SPRINT_QUALIFYING, 45)
        assert session is not None
        assert session.end_datetime - session.start_datetime == timedelta(minutes=45)

    def test_session_title_from_session_type(self) -> None:
        data = {"date": "2024-03-01", "time": "15:00:00Z"}
        session = _build_session(data, SessionType.QUALIFYING, 60)
        assert session is not None
        assert session.title == "Qualifying"


# ---------------------------------------------------------------------------
# TestBuildEvent
# ---------------------------------------------------------------------------


class TestBuildEvent:
    def test_event_fields_from_race_data(self) -> None:
        champ = _make_championship(2024)
        event = _build_event(champ, _BAHRAIN_RACE)
        assert event.name == "Bahrain Grand Prix"
        assert event.season == 2024
        assert event.round == 1

    def test_event_uid_format(self) -> None:
        champ = _make_championship(2024)
        event = _build_event(champ, _BAHRAIN_RACE)
        assert event.event_uid == "jolpica-2024-1@motorsport-calendar"

    def test_event_includes_race_session(self) -> None:
        champ = _make_championship(2024)
        event = _build_event(champ, _BAHRAIN_RACE)
        types = {s.type for s in event.sessions}
        assert SessionType.RACE in types

    def test_sessions_sorted_by_start_datetime(self) -> None:
        champ = _make_championship(2024)
        event = _build_event(champ, _BAHRAIN_RACE)
        starts = [s.start_datetime for s in event.sessions]
        assert starts == sorted(starts)

    def test_missing_session_field_is_skipped(self) -> None:
        race_no_fp3 = {k: v for k, v in _BAHRAIN_RACE.items() if k != "ThirdPractice"}
        champ = _make_championship(2024)
        event = _build_event(champ, race_no_fp3)
        types = {s.type for s in event.sessions}
        assert SessionType.FP3 not in types

    def test_historical_race_without_time_uses_noon_utc(self) -> None:
        champ = _make_championship(1950)
        event = _build_event(champ, _HISTORICAL_RACE)
        race_sessions = [s for s in event.sessions if s.type == SessionType.RACE]
        assert len(race_sessions) == 1
        assert race_sessions[0].start_datetime.hour == 12


# ---------------------------------------------------------------------------
# TestGetSeasonHappyPath
# ---------------------------------------------------------------------------


class TestGetSeasonHappyPath:
    async def test_one_race_produces_one_event(self) -> None:
        client = _make_client([_BAHRAIN_RACE])
        events = await JolpicaSource(client).get_season(2024)
        assert len(events) == 1

    async def test_empty_races_returns_empty_list(self) -> None:
        client = _make_client([])
        events = await JolpicaSource(client).get_season(2024)
        assert events == []

    async def test_multiple_races_produce_multiple_events(self) -> None:
        client = _make_client([_BAHRAIN_RACE, _AUSTRALIA_RACE])
        events = await JolpicaSource(client).get_season(2024)
        assert len(events) == 2

    async def test_sprint_weekend_includes_sprint_and_sprint_qualifying(self) -> None:
        client = _make_client([_CHINA_SPRINT_RACE])
        events = await JolpicaSource(client).get_season(2024)
        types = {s.type for s in events[0].sessions}
        assert SessionType.SPRINT in types
        assert SessionType.SPRINT_QUALIFYING in types

    async def test_sessions_sorted_chronologically(self) -> None:
        client = _make_client([_BAHRAIN_RACE])
        events = await JolpicaSource(client).get_season(2024)
        starts = [s.start_datetime for s in events[0].sessions]
        assert starts == sorted(starts)

    async def test_typical_race_weekend_session_count(self) -> None:
        # FP1 + FP2 + FP3 + Qualifying + Race = 5 sessions
        client = _make_client([_BAHRAIN_RACE])
        events = await JolpicaSource(client).get_season(2024)
        assert len(events[0].sessions) == 5

    async def test_championship_is_formula1_single_seater(self) -> None:
        client = _make_client([_BAHRAIN_RACE])
        events = await JolpicaSource(client).get_season(2024)
        champ = events[0].championship
        assert champ.category == ChampionshipCategory.SINGLE_SEATER
        assert "Formula 1" in champ.name


# ---------------------------------------------------------------------------
# TestGetSeasonEventFields
# ---------------------------------------------------------------------------


class TestGetSeasonEventFields:
    async def test_event_name_from_race_name(self) -> None:
        client = _make_client([_BAHRAIN_RACE])
        events = await JolpicaSource(client).get_season(2024)
        assert events[0].name == "Bahrain Grand Prix"

    async def test_event_season_from_race_season(self) -> None:
        client = _make_client([_BAHRAIN_RACE])
        events = await JolpicaSource(client).get_season(2024)
        assert events[0].season == 2024

    async def test_event_round_from_race_round(self) -> None:
        client = _make_client([_BAHRAIN_RACE])
        events = await JolpicaSource(client).get_season(2024)
        assert events[0].round == 1

    async def test_championship_id_contains_year(self) -> None:
        client = _make_client([_BAHRAIN_RACE])
        events = await JolpicaSource(client).get_season(2024)
        assert "2024" in events[0].championship.id

    async def test_event_uid_is_stable_across_calls(self) -> None:
        e1 = await JolpicaSource(_make_client([_BAHRAIN_RACE])).get_season(2024)
        e2 = await JolpicaSource(_make_client([_BAHRAIN_RACE])).get_season(2024)
        assert e1[0].event_uid == e2[0].event_uid


# ---------------------------------------------------------------------------
# TestGetSeasonCircuitFields
# ---------------------------------------------------------------------------


class TestGetSeasonCircuitFields:
    async def test_circuit_timezone_resolved(self) -> None:
        client = _make_client([_BAHRAIN_RACE])
        events = await JolpicaSource(client).get_season(2024)
        assert events[0].circuit.timezone == "Asia/Bahrain"

    async def test_circuit_city_from_locality(self) -> None:
        client = _make_client([_BAHRAIN_RACE])
        events = await JolpicaSource(client).get_season(2024)
        assert events[0].circuit.city == "Sakhir"

    async def test_circuit_country_from_location(self) -> None:
        client = _make_client([_AUSTRALIA_RACE])
        events = await JolpicaSource(client).get_season(2024)
        assert events[0].circuit.country == "Australia"

    async def test_unknown_circuit_timezone_is_utc(self) -> None:
        unknown_circuit_race = {
            **_BAHRAIN_RACE,
            "Circuit": {
                "circuitId": "nowhere",
                "circuitName": "Nowhere GP",
                "Location": {"locality": "Nowhere", "country": "Neverland"},
            },
        }
        client = _make_client([unknown_circuit_race])
        events = await JolpicaSource(client).get_season(2024)
        assert events[0].circuit.timezone == "UTC"


# ---------------------------------------------------------------------------
# TestGetSeasonErrors
# ---------------------------------------------------------------------------


class TestGetSeasonErrors:
    async def test_http_404_propagates(self) -> None:
        client = _make_error_client(404)
        with pytest.raises(httpx.HTTPStatusError):
            await JolpicaSource(client).get_season(2024)

    async def test_http_500_propagates(self) -> None:
        client = _make_error_client(500)
        with pytest.raises(httpx.HTTPStatusError):
            await JolpicaSource(client).get_season(2024)

    async def test_timeout_propagates(self) -> None:
        client = _make_timeout_client()
        with pytest.raises(httpx.TimeoutException):
            await JolpicaSource(client).get_season(2024)


# ---------------------------------------------------------------------------
# TestSourceConstruction
# ---------------------------------------------------------------------------


class TestSourceConstruction:
    def test_cache_disabled_when_client_injected(self) -> None:
        client = MagicMock(spec=httpx.AsyncClient)
        source = JolpicaSource(client=client)
        assert source._cache is None

    def test_cache_enabled_when_no_client_given(self) -> None:
        source = JolpicaSource.__new__(JolpicaSource)
        # Test the logic directly without triggering the real HttpCache()/httpx constructor
        from unittest.mock import patch

        target = "motorsport_calendar.providers.formula1.sources.jolpica.HttpCache"
        with patch(target) as mock_cache:
            mock_cache.return_value = object()
            source = JolpicaSource()
            assert source._cache is not None

    def test_explicit_none_cache_with_injected_client_is_none(self) -> None:
        client = MagicMock(spec=httpx.AsyncClient)
        source = JolpicaSource(client=client, cache=None)
        assert source._cache is None

    def test_refresh_flag_stored(self) -> None:
        client = MagicMock(spec=httpx.AsyncClient)
        source = JolpicaSource(client=client, refresh=True)
        assert source._refresh is True

    def test_refresh_defaults_to_false(self) -> None:
        client = MagicMock(spec=httpx.AsyncClient)
        source = JolpicaSource(client=client)
        assert source._refresh is False
