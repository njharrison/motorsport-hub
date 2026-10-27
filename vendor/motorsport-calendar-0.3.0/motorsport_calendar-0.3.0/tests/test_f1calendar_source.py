"""Tests for F1CalendarSource — all HTTP calls are mocked."""

from __future__ import annotations

from datetime import timedelta
from typing import Any
from unittest.mock import MagicMock

import httpx
import pytest

from motorsport_calendar.core.datasource import JsonDataSource
from motorsport_calendar.models import ChampionshipCategory, SessionType
from motorsport_calendar.providers.formula2.source import Formula2Source
from motorsport_calendar.providers.formula2.sources.f1calendar import (
    F1CalendarSource,
    _build_circuit,
    _build_event,
    _build_session,
    _make_championship,
    _resolve_circuit_data,
)

# ---------------------------------------------------------------------------
# Fixtures — realistic f1calendar JSON payloads
# ---------------------------------------------------------------------------

_BAHRAIN_EVENT: dict[str, Any] = {
    "name": "Bahrain Grand Prix",
    "location": "Sakhir",
    "round": 1,
    "slug": "bahrain",
    "localeKey": "bahrain",
    "sessions": {
        "fp1": "2024-02-29T11:05:00Z",
        "qualifying": "2024-03-01T12:10:00Z",
        "sprintRace": "2024-03-02T09:05:00Z",
        "feature": "2024-03-03T10:05:00Z",
    },
}

_AUSTRALIA_EVENT: dict[str, Any] = {
    "name": "Australian Grand Prix",
    "location": "Melbourne",
    "round": 3,
    "slug": "albert_park",
    "localeKey": "albert_park",
    "sessions": {
        "fp1": "2024-03-22T01:30:00Z",
        "qualifying": "2024-03-22T05:00:00Z",
        "sprintRace": "2024-03-23T02:45:00Z",
        "feature": "2024-03-24T03:05:00Z",
    },
}

# Sprint weekend without FP1 (some F2 rounds)
_MONACO_EVENT_NO_FP: dict[str, Any] = {
    "name": "Monaco Grand Prix",
    "location": "Monte-Carlo",
    "round": 8,
    "slug": "monaco",
    "localeKey": "monaco",
    "sessions": {
        "qualifying": "2024-05-24T13:00:00Z",
        "sprintRace": "2024-05-25T10:35:00Z",
        "feature": "2024-05-26T09:05:00Z",
    },
}

_F1CALENDAR_ONE_RACE: dict[str, Any] = {
    "name": "Formula 2",
    "races": [_BAHRAIN_EVENT],
}

_F1CALENDAR_TWO_RACES: dict[str, Any] = {
    "name": "Formula 2",
    "races": [_BAHRAIN_EVENT, _AUSTRALIA_EVENT],
}

_F1CALENDAR_EMPTY: dict[str, Any] = {
    "name": "Formula 2",
    "races": [],
}


# ---------------------------------------------------------------------------
# Mock client helpers
# ---------------------------------------------------------------------------


def _make_client(response_data: dict) -> MagicMock:
    """Fake httpx.AsyncClient that returns the given dict as JSON."""

    async def get(url: str, *, params: dict | None = None) -> MagicMock:
        resp = MagicMock(spec=httpx.Response)
        resp.raise_for_status.return_value = None
        resp.json.return_value = response_data
        return resp

    client = MagicMock(spec=httpx.AsyncClient)
    client.get = get
    return client


def _make_error_client(status_code: int) -> MagicMock:
    async def get(url: str, *, params: dict | None = None) -> MagicMock:
        request = httpx.Request("GET", url)
        response = httpx.Response(status_code, request=request)
        raise httpx.HTTPStatusError(f"HTTP {status_code}", request=request, response=response)

    client = MagicMock(spec=httpx.AsyncClient)
    client.get = get
    return client


def _make_timeout_client() -> MagicMock:
    async def get(url: str, *, params: dict | None = None) -> MagicMock:
        raise httpx.TimeoutException("timeout")

    client = MagicMock(spec=httpx.AsyncClient)
    client.get = get
    return client


# ---------------------------------------------------------------------------
# TestSourceInheritance
# ---------------------------------------------------------------------------


class TestSourceInheritance:
    def test_is_formula2_source(self) -> None:
        assert issubclass(F1CalendarSource, Formula2Source)

    def test_is_json_data_source(self) -> None:
        assert issubclass(F1CalendarSource, JsonDataSource)

    def test_instance_is_formula2_source(self) -> None:
        client = MagicMock(spec=httpx.AsyncClient)
        assert isinstance(F1CalendarSource(client=client), Formula2Source)

    def test_instance_is_json_data_source(self) -> None:
        client = MagicMock(spec=httpx.AsyncClient)
        assert isinstance(F1CalendarSource(client=client), JsonDataSource)


# ---------------------------------------------------------------------------
# TestResolveCircuitData
# ---------------------------------------------------------------------------


class TestResolveCircuitData:
    def test_known_slug_returns_country_and_timezone(self) -> None:
        country, tz = _resolve_circuit_data("bahrain")
        assert country == "Bahrain"
        assert tz == "Asia/Bahrain"

    def test_albert_park_returns_australia(self) -> None:
        country, tz = _resolve_circuit_data("albert_park")
        assert country == "Australia"
        assert tz == "Australia/Melbourne"

    def test_unknown_slug_returns_fallback(self) -> None:
        country, tz = _resolve_circuit_data("nowhere")
        assert country == "Unknown"
        assert tz == "UTC"

    def test_empty_slug_returns_fallback(self) -> None:
        country, tz = _resolve_circuit_data("")
        assert country == "Unknown"
        assert tz == "UTC"


# ---------------------------------------------------------------------------
# TestBuildCircuit
# ---------------------------------------------------------------------------


class TestBuildCircuit:
    def test_fields_mapped_correctly(self) -> None:
        circuit = _build_circuit(_BAHRAIN_EVENT)
        assert circuit.id == "f1calendar-f2-bahrain"
        assert circuit.city == "Sakhir"
        assert circuit.country == "Bahrain"
        assert circuit.timezone == "Asia/Bahrain"

    def test_unknown_slug_uses_fallback(self) -> None:
        event = {**_BAHRAIN_EVENT, "slug": "nowhere", "localeKey": "nowhere"}
        circuit = _build_circuit(event)
        assert circuit.country == "Unknown"
        assert circuit.timezone == "UTC"


# ---------------------------------------------------------------------------
# TestBuildSession
# ---------------------------------------------------------------------------


class TestBuildSession:
    def test_complete_session_is_built(self) -> None:
        session = _build_session("2024-03-03T10:05:00Z", SessionType.RACE, 65, "Feature Race")
        assert session is not None
        assert session.type == SessionType.RACE
        assert session.title == "Feature Race"
        assert session.start_datetime.tzinfo is not None
        assert session.end_datetime.tzinfo is not None

    def test_end_datetime_inferred_from_duration(self) -> None:
        session = _build_session("2024-03-01T12:10:00Z", SessionType.QUALIFYING, 30, "Qualifying")
        assert session is not None
        assert session.end_datetime - session.start_datetime == timedelta(minutes=30)

    def test_invalid_timestamp_returns_none(self) -> None:
        assert _build_session("not-a-date", SessionType.RACE, 65, "Feature Race") is None

    def test_naive_datetime_returns_none(self) -> None:
        # No Z suffix → naive datetime
        assert _build_session("2024-03-03T10:05:00", SessionType.RACE, 65, "Feature Race") is None

    def test_none_timestamp_returns_none(self) -> None:
        assert _build_session(None, SessionType.RACE, 65, "Feature Race") is None  # type: ignore[arg-type]

    def test_sprint_race_duration_is_45_minutes(self) -> None:
        session = _build_session("2024-03-02T09:05:00Z", SessionType.SPRINT, 45, "Sprint Race")
        assert session is not None
        assert session.end_datetime - session.start_datetime == timedelta(minutes=45)

    def test_fp_duration_is_45_minutes(self) -> None:
        session = _build_session("2024-02-29T11:05:00Z", SessionType.FP1, 45, "Free Practice")
        assert session is not None
        assert session.end_datetime - session.start_datetime == timedelta(minutes=45)


# ---------------------------------------------------------------------------
# TestBuildEvent
# ---------------------------------------------------------------------------


class TestBuildEvent:
    def test_event_fields_from_event_data(self) -> None:
        champ = _make_championship(2024)
        event = _build_event(champ, _BAHRAIN_EVENT, 2024)
        assert event.name == "Bahrain Grand Prix"
        assert event.season == 2024
        assert event.round == 1

    def test_event_uid_format(self) -> None:
        champ = _make_championship(2024)
        event = _build_event(champ, _BAHRAIN_EVENT, 2024)
        assert event.event_uid == "f1calendar-f2-2024-1@motorsport-calendar"

    def test_all_four_sessions_included(self) -> None:
        champ = _make_championship(2024)
        event = _build_event(champ, _BAHRAIN_EVENT, 2024)
        assert len(event.sessions) == 4

    def test_sessions_sorted_chronologically(self) -> None:
        champ = _make_championship(2024)
        event = _build_event(champ, _BAHRAIN_EVENT, 2024)
        starts = [s.start_datetime for s in event.sessions]
        assert starts == sorted(starts)

    def test_missing_session_key_is_skipped(self) -> None:
        champ = _make_championship(2024)
        event = _build_event(champ, _MONACO_EVENT_NO_FP, 2024)
        types = {s.type for s in event.sessions}
        assert SessionType.FP1 not in types
        assert SessionType.RACE in types

    def test_session_types_correct(self) -> None:
        champ = _make_championship(2024)
        event = _build_event(champ, _BAHRAIN_EVENT, 2024)
        types = {s.type for s in event.sessions}
        assert SessionType.FP1 in types
        assert SessionType.QUALIFYING in types
        assert SessionType.SPRINT in types
        assert SessionType.RACE in types

    def test_feature_race_title(self) -> None:
        champ = _make_championship(2024)
        event = _build_event(champ, _BAHRAIN_EVENT, 2024)
        race = next(s for s in event.sessions if s.type == SessionType.RACE)
        assert race.title == "Feature Race"

    def test_sprint_race_title(self) -> None:
        champ = _make_championship(2024)
        event = _build_event(champ, _BAHRAIN_EVENT, 2024)
        sprint = next(s for s in event.sessions if s.type == SessionType.SPRINT)
        assert sprint.title == "Sprint Race"


# ---------------------------------------------------------------------------
# TestGetSeasonHappyPath
# ---------------------------------------------------------------------------


class TestGetSeasonHappyPath:
    async def test_one_event_produces_one_event(self) -> None:
        client = _make_client(_F1CALENDAR_ONE_RACE)
        events = await F1CalendarSource(client).get_season(2024)
        assert len(events) == 1

    async def test_empty_events_returns_empty_list(self) -> None:
        client = _make_client(_F1CALENDAR_EMPTY)
        events = await F1CalendarSource(client).get_season(2024)
        assert events == []

    async def test_multiple_events_produce_multiple_events(self) -> None:
        client = _make_client(_F1CALENDAR_TWO_RACES)
        events = await F1CalendarSource(client).get_season(2024)
        assert len(events) == 2

    async def test_event_name_from_event_data(self) -> None:
        client = _make_client(_F1CALENDAR_ONE_RACE)
        events = await F1CalendarSource(client).get_season(2024)
        assert events[0].name == "Bahrain Grand Prix"

    async def test_event_season_is_year_parameter(self) -> None:
        client = _make_client(_F1CALENDAR_ONE_RACE)
        events = await F1CalendarSource(client).get_season(2024)
        assert events[0].season == 2024

    async def test_event_round_from_json(self) -> None:
        client = _make_client(_F1CALENDAR_ONE_RACE)
        events = await F1CalendarSource(client).get_season(2024)
        assert events[0].round == 1

    async def test_championship_is_formula2_single_seater(self) -> None:
        client = _make_client(_F1CALENDAR_ONE_RACE)
        events = await F1CalendarSource(client).get_season(2024)
        champ = events[0].championship
        assert champ.category == ChampionshipCategory.SINGLE_SEATER
        assert "Formula 2" in champ.name

    async def test_championship_id_contains_year(self) -> None:
        client = _make_client(_F1CALENDAR_ONE_RACE)
        events = await F1CalendarSource(client).get_season(2024)
        assert "2024" in events[0].championship.id

    async def test_circuit_timezone_resolved(self) -> None:
        client = _make_client(_F1CALENDAR_ONE_RACE)
        events = await F1CalendarSource(client).get_season(2024)
        assert events[0].circuit.timezone == "Asia/Bahrain"

    async def test_circuit_city_from_location(self) -> None:
        client = _make_client(_F1CALENDAR_ONE_RACE)
        events = await F1CalendarSource(client).get_season(2024)
        assert events[0].circuit.city == "Sakhir"

    async def test_event_has_four_sessions(self) -> None:
        client = _make_client(_F1CALENDAR_ONE_RACE)
        events = await F1CalendarSource(client).get_season(2024)
        assert len(events[0].sessions) == 4

    async def test_event_uid_is_stable(self) -> None:
        e1 = await F1CalendarSource(_make_client(_F1CALENDAR_ONE_RACE)).get_season(2024)
        e2 = await F1CalendarSource(_make_client(_F1CALENDAR_ONE_RACE)).get_season(2024)
        assert e1[0].event_uid == e2[0].event_uid


# ---------------------------------------------------------------------------
# TestGetSeasonErrors
# ---------------------------------------------------------------------------


class TestGetSeasonErrors:
    async def test_http_404_propagates(self) -> None:
        client = _make_error_client(404)
        with pytest.raises(httpx.HTTPStatusError):
            await F1CalendarSource(client).get_season(2024)

    async def test_http_500_propagates(self) -> None:
        client = _make_error_client(500)
        with pytest.raises(httpx.HTTPStatusError):
            await F1CalendarSource(client).get_season(2024)

    async def test_timeout_propagates(self) -> None:
        client = _make_timeout_client()
        with pytest.raises(httpx.TimeoutException):
            await F1CalendarSource(client).get_season(2024)


# ---------------------------------------------------------------------------
# TestSourceConstruction
# ---------------------------------------------------------------------------


class TestSourceConstruction:
    def test_cache_disabled_when_client_injected(self) -> None:
        client = MagicMock(spec=httpx.AsyncClient)
        source = F1CalendarSource(client=client)
        assert source._cache is None

    def test_cache_enabled_when_no_client(self) -> None:
        from unittest.mock import patch

        target = "motorsport_calendar.providers.support_series.f1calendar_base.HttpCache"
        with patch(target) as mock_cache:
            mock_cache.return_value = object()
            source = F1CalendarSource()
            assert source._cache is not None

    def test_refresh_flag_stored(self) -> None:
        client = MagicMock(spec=httpx.AsyncClient)
        source = F1CalendarSource(client=client, refresh=True)
        assert source._refresh is True

    def test_refresh_defaults_to_false(self) -> None:
        client = MagicMock(spec=httpx.AsyncClient)
        source = F1CalendarSource(client=client)
        assert source._refresh is False
