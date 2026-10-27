"""Tests for F1CalendarBaseSource — the shared framework for support series."""

from __future__ import annotations

from datetime import timedelta
from typing import Any
from unittest.mock import MagicMock

import httpx
import pytest

from motorsport_calendar.core.datasource import JsonDataSource
from motorsport_calendar.models import (
    Championship,
    ChampionshipCategory,
    SessionType,
)
from motorsport_calendar.providers.support_series.f1calendar_base import (
    F1CalendarBaseSource,
    _build_session,
)

# ---------------------------------------------------------------------------
# Minimal concrete implementation used across all tests
# ---------------------------------------------------------------------------

_CIRCUIT_DATA = {
    "monaco": ("Monaco", "Europe/Monaco"),
    "spa": ("Belgium", "Europe/Brussels"),
}

_SESSION_MAP: dict[str, tuple[SessionType, int, str]] = {
    "qualifying": (SessionType.QUALIFYING, 30, "Qualifying"),
    "race": (SessionType.RACE, 60, "Race"),
}

_TEST_EVENT: dict[str, Any] = {
    "name": "Monaco GP",
    "location": "Monte-Carlo",
    "round": 1,
    "slug": "monaco",
    "localeKey": "monaco",
    "sessions": {
        "qualifying": "2024-05-24T13:00:00Z",
        "race": "2024-05-26T13:00:00Z",
    },
}

_TEST_RESPONSE: dict[str, Any] = {
    "name": "Test Series",
    "races": [_TEST_EVENT],
}

_EMPTY_RESPONSE: dict[str, Any] = {"name": "Test Series", "races": []}


class _ConcreteSource(F1CalendarBaseSource):
    """Minimal concrete implementation for testing base class behaviour."""

    @property
    def _series_key(self) -> str:
        return "test"

    @property
    def _session_map(self) -> dict[str, tuple[SessionType, int, str]]:
        return _SESSION_MAP

    @property
    def _circuit_data(self) -> dict[str, tuple[str, str]]:
        return _CIRCUIT_DATA

    def _make_championship(self, year: int) -> Championship:
        return Championship(
            id=f"test-{year}",
            name="Test Series",
            category=ChampionshipCategory.SINGLE_SEATER,
        )


def _make_client(response_data: dict) -> MagicMock:
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


# ---------------------------------------------------------------------------
# TestAbstractness
# ---------------------------------------------------------------------------


class TestAbstractness:
    def test_cannot_instantiate_base_directly(self) -> None:
        with pytest.raises(TypeError):
            F1CalendarBaseSource()  # type: ignore[abstract]

    def test_missing_series_key_prevents_instantiation(self) -> None:
        class _Incomplete(F1CalendarBaseSource):
            @property
            def _session_map(self):
                return {}

            @property
            def _circuit_data(self):
                return {}

            def _make_championship(self, year):
                return None

        with pytest.raises(TypeError):
            _Incomplete()  # type: ignore[abstract]

    def test_missing_session_map_prevents_instantiation(self) -> None:
        class _Incomplete(F1CalendarBaseSource):
            @property
            def _series_key(self):
                return "x"

            @property
            def _circuit_data(self):
                return {}

            def _make_championship(self, year):
                return None

        with pytest.raises(TypeError):
            _Incomplete()  # type: ignore[abstract]

    def test_missing_circuit_data_prevents_instantiation(self) -> None:
        class _Incomplete(F1CalendarBaseSource):
            @property
            def _series_key(self):
                return "x"

            @property
            def _session_map(self):
                return {}

            def _make_championship(self, year):
                return None

        with pytest.raises(TypeError):
            _Incomplete()  # type: ignore[abstract]

    def test_missing_make_championship_prevents_instantiation(self) -> None:
        class _Incomplete(F1CalendarBaseSource):
            @property
            def _series_key(self):
                return "x"

            @property
            def _session_map(self):
                return {}

            @property
            def _circuit_data(self):
                return {}

        with pytest.raises(TypeError):
            _Incomplete()  # type: ignore[abstract]

    def test_complete_subclass_is_json_data_source(self) -> None:
        assert issubclass(_ConcreteSource, JsonDataSource)

    def test_complete_subclass_can_be_instantiated(self) -> None:
        client = MagicMock(spec=httpx.AsyncClient)
        source = _ConcreteSource(client=client)
        assert source is not None


# ---------------------------------------------------------------------------
# TestConstruction
# ---------------------------------------------------------------------------


class TestConstruction:
    def test_cache_disabled_when_client_injected(self) -> None:
        client = MagicMock(spec=httpx.AsyncClient)
        source = _ConcreteSource(client=client)
        assert source._cache is None

    def test_refresh_defaults_to_false(self) -> None:
        client = MagicMock(spec=httpx.AsyncClient)
        assert _ConcreteSource(client=client)._refresh is False

    def test_refresh_flag_stored(self) -> None:
        client = MagicMock(spec=httpx.AsyncClient)
        assert _ConcreteSource(client=client, refresh=True)._refresh is True

    def test_custom_client_is_stored(self) -> None:
        client = MagicMock(spec=httpx.AsyncClient)
        assert _ConcreteSource(client=client)._client is client


# ---------------------------------------------------------------------------
# TestGetSeason — template method
# ---------------------------------------------------------------------------


class TestGetSeason:
    async def test_one_event_produces_one_event(self) -> None:
        events = await _ConcreteSource(_make_client(_TEST_RESPONSE)).get_season(2024)
        assert len(events) == 1

    async def test_empty_events_returns_empty_list(self) -> None:
        events = await _ConcreteSource(_make_client(_EMPTY_RESPONSE)).get_season(2024)
        assert events == []

    async def test_url_contains_series_key(self) -> None:
        calls: list[str] = []

        async def get(url: str, *, params: dict | None = None) -> MagicMock:
            calls.append(url)
            resp = MagicMock(spec=httpx.Response)
            resp.raise_for_status.return_value = None
            resp.json.return_value = _EMPTY_RESPONSE
            return resp

        client = MagicMock(spec=httpx.AsyncClient)
        client.get = get
        await _ConcreteSource(client).get_season(2024)
        assert "test" in calls[0]

    async def test_url_contains_year(self) -> None:
        calls: list[str] = []

        async def get(url: str, *, params: dict | None = None) -> MagicMock:
            calls.append(url)
            resp = MagicMock(spec=httpx.Response)
            resp.raise_for_status.return_value = None
            resp.json.return_value = _EMPTY_RESPONSE
            return resp

        client = MagicMock(spec=httpx.AsyncClient)
        client.get = get
        await _ConcreteSource(client).get_season(2025)
        assert "2025" in calls[0]

    async def test_championship_id_contains_year(self) -> None:
        events = await _ConcreteSource(_make_client(_TEST_RESPONSE)).get_season(2024)
        assert "2024" in events[0].championship.id

    async def test_http_error_propagates(self) -> None:
        with pytest.raises(httpx.HTTPStatusError):
            await _ConcreteSource(_make_error_client(404)).get_season(2024)


# ---------------------------------------------------------------------------
# TestResolveCircuitData — via instance method
# ---------------------------------------------------------------------------


class TestResolveCircuitData:
    def test_known_slug_returns_data(self) -> None:
        client = MagicMock(spec=httpx.AsyncClient)
        source = _ConcreteSource(client=client)
        country, tz = source._resolve_circuit_data("monaco")
        assert country == "Monaco"
        assert tz == "Europe/Monaco"

    def test_unknown_slug_returns_fallback(self) -> None:
        client = MagicMock(spec=httpx.AsyncClient)
        source = _ConcreteSource(client=client)
        country, tz = source._resolve_circuit_data("nowhere")
        assert country == "Unknown"
        assert tz == "UTC"


# ---------------------------------------------------------------------------
# TestBuildCircuit — via instance method
# ---------------------------------------------------------------------------


class TestBuildCircuit:
    def test_circuit_id_uses_series_key(self) -> None:
        client = MagicMock(spec=httpx.AsyncClient)
        source = _ConcreteSource(client=client)
        circuit = source._build_circuit(_TEST_EVENT)
        assert circuit.id == "f1calendar-test-monaco"

    def test_circuit_city_from_location(self) -> None:
        client = MagicMock(spec=httpx.AsyncClient)
        source = _ConcreteSource(client=client)
        circuit = source._build_circuit(_TEST_EVENT)
        assert circuit.city == "Monte-Carlo"

    def test_circuit_country_from_circuit_data(self) -> None:
        client = MagicMock(spec=httpx.AsyncClient)
        source = _ConcreteSource(client=client)
        circuit = source._build_circuit(_TEST_EVENT)
        assert circuit.country == "Monaco"

    def test_circuit_timezone_from_circuit_data(self) -> None:
        client = MagicMock(spec=httpx.AsyncClient)
        source = _ConcreteSource(client=client)
        circuit = source._build_circuit(_TEST_EVENT)
        assert circuit.timezone == "Europe/Monaco"

    def test_unknown_slug_falls_back(self) -> None:
        client = MagicMock(spec=httpx.AsyncClient)
        source = _ConcreteSource(client=client)
        event = {**_TEST_EVENT, "slug": "nowhere"}
        circuit = source._build_circuit(event)
        assert circuit.country == "Unknown"
        assert circuit.timezone == "UTC"


# ---------------------------------------------------------------------------
# TestBuildEvent — via instance method
# ---------------------------------------------------------------------------


class TestBuildEvent:
    def _source(self) -> _ConcreteSource:
        return _ConcreteSource(client=MagicMock(spec=httpx.AsyncClient))

    def test_event_uid_contains_series_key(self) -> None:
        champ = self._source()._make_championship(2024)
        event = self._source()._build_event(champ, _TEST_EVENT, 2024)
        assert "f1calendar-test-2024-1" in event.event_uid

    def test_sessions_from_session_map(self) -> None:
        champ = self._source()._make_championship(2024)
        event = self._source()._build_event(champ, _TEST_EVENT, 2024)
        types = {s.type for s in event.sessions}
        assert SessionType.QUALIFYING in types
        assert SessionType.RACE in types

    def test_missing_session_key_skipped(self) -> None:
        data = {**_TEST_EVENT, "sessions": {"race": "2024-05-26T13:00:00Z"}}
        champ = self._source()._make_championship(2024)
        event = self._source()._build_event(champ, data, 2024)
        types = {s.type for s in event.sessions}
        assert SessionType.QUALIFYING not in types
        assert SessionType.RACE in types

    def test_sessions_sorted_chronologically(self) -> None:
        champ = self._source()._make_championship(2024)
        event = self._source()._build_event(champ, _TEST_EVENT, 2024)
        starts = [s.start_datetime for s in event.sessions]
        assert starts == sorted(starts)

    def test_event_name_from_data(self) -> None:
        champ = self._source()._make_championship(2024)
        event = self._source()._build_event(champ, _TEST_EVENT, 2024)
        assert event.name == "Monaco GP"

    def test_event_round_from_data(self) -> None:
        champ = self._source()._make_championship(2024)
        event = self._source()._build_event(champ, _TEST_EVENT, 2024)
        assert event.round == 1


# ---------------------------------------------------------------------------
# TestBuildSession — module-level pure function
# ---------------------------------------------------------------------------


class TestBuildSession:
    def test_valid_utc_timestamp(self) -> None:
        session = _build_session("2024-05-26T13:00:00Z", SessionType.RACE, 60, "Race")
        assert session is not None
        assert session.type == SessionType.RACE

    def test_duration_inferred(self) -> None:
        session = _build_session("2024-05-26T13:00:00Z", SessionType.RACE, 60, "Race")
        assert session is not None
        assert session.end_datetime - session.start_datetime == timedelta(minutes=60)

    def test_invalid_timestamp_returns_none(self) -> None:
        assert _build_session("not-a-date", SessionType.RACE, 60, "Race") is None

    def test_none_returns_none(self) -> None:
        assert _build_session(None, SessionType.RACE, 60, "Race") is None  # type: ignore[arg-type]

    def test_naive_datetime_returns_none(self) -> None:
        assert _build_session("2024-05-26T13:00:00", SessionType.RACE, 60, "Race") is None

    def test_title_stored(self) -> None:
        session = _build_session("2024-05-26T13:00:00Z", SessionType.RACE, 60, "Feature Race")
        assert session is not None
        assert session.title == "Feature Race"


# ---------------------------------------------------------------------------
# TestRacesKeyRegression — Sprint QA-03
# Documents that the dataset uses "races", not "events".
# ---------------------------------------------------------------------------


class TestRacesKeyRegression:
    async def test_races_key_returns_events(self) -> None:
        """Dataset uses 'races' as the top-level key — must be non-empty."""
        source = _ConcreteSource(_make_client({"races": [_TEST_EVENT]}))
        events = await source.get_season(2024)
        assert len(events) == 1

    async def test_events_key_is_ignored(self) -> None:
        """Legacy 'events' key must NOT be read — regression guard."""
        source = _ConcreteSource(_make_client({"events": [_TEST_EVENT]}))
        events = await source.get_season(2024)
        assert events == []

    async def test_both_keys_present_reads_only_races(self) -> None:
        """If both keys exist, only 'races' is read."""
        source = _ConcreteSource(_make_client({"races": [_TEST_EVENT], "events": []}))
        events = await source.get_season(2024)
        assert len(events) == 1
