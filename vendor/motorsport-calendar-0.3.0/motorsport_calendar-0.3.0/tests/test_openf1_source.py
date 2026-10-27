"""Tests for OpenF1Source — all HTTP calls are mocked."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import httpx
import pytest

from motorsport_calendar.models import ChampionshipCategory, SessionType
from motorsport_calendar.providers.formula1.sources.openf1 import (
    OpenF1Source,
    _build_circuit,
    _build_session,
    _parse_session_type,
    _resolve_timezone,
)

# ---------------------------------------------------------------------------
# Fixtures — realistic OpenF1 API payloads
# ---------------------------------------------------------------------------

_BAHRAIN_MEETING: dict[str, Any] = {
    "meeting_key": 1229,
    "meeting_name": "Bahrain Grand Prix",
    "meeting_official_name": "FORMULA 1 GULF AIR BAHRAIN GRAND PRIX 2024",
    "location": "Sakhir",
    "country_name": "Bahrain",
    "country_code": "BHR",
    "circuit_key": 1,
    "circuit_short_name": "Sakhir",
    "date_start": "2024-02-29T11:00:00+00:00",
    "gmt_offset": "03:00:00",
    "year": 2024,
}

_AUSTRALIA_MEETING: dict[str, Any] = {
    "meeting_key": 1230,
    "meeting_name": "Australian Grand Prix",
    "meeting_official_name": "FORMULA 1 ROLEX AUSTRALIAN GRAND PRIX 2024",
    "location": "Melbourne",
    "country_name": "Australia",
    "country_code": "AUS",
    "circuit_key": 2,
    "circuit_short_name": "Albert Park",
    "date_start": "2024-03-14T01:30:00+00:00",
    "gmt_offset": "11:00:00",
    "year": 2024,
}

_BAHRAIN_FP1: dict[str, Any] = {
    "session_key": 9472,
    "session_name": "Practice 1",
    "session_type": "Practice",
    "date_start": "2024-02-29T11:30:00+00:00",
    "date_end": "2024-02-29T12:30:00+00:00",
    "meeting_key": 1229,
    "gmt_offset": "03:00:00",
    "location": "Sakhir",
    "country_name": "Bahrain",
    "circuit_key": 1,
    "circuit_short_name": "Sakhir",
    "year": 2024,
}

_BAHRAIN_QUALIFYING: dict[str, Any] = {
    "session_key": 9474,
    "session_name": "Qualifying",
    "session_type": "Qualifying",
    "date_start": "2024-03-01T15:00:00+00:00",
    "date_end": "2024-03-01T16:00:00+00:00",
    "meeting_key": 1229,
    "gmt_offset": "03:00:00",
    "location": "Sakhir",
    "country_name": "Bahrain",
    "circuit_key": 1,
    "circuit_short_name": "Sakhir",
    "year": 2024,
}

_BAHRAIN_RACE: dict[str, Any] = {
    "session_key": 9475,
    "session_name": "Race",
    "session_type": "Race",
    "date_start": "2024-03-02T15:00:00+00:00",
    "date_end": "2024-03-02T17:00:00+00:00",
    "meeting_key": 1229,
    "gmt_offset": "03:00:00",
    "location": "Sakhir",
    "country_name": "Bahrain",
    "circuit_key": 1,
    "circuit_short_name": "Sakhir",
    "year": 2024,
}


# ---------------------------------------------------------------------------
# Mock client factory
# ---------------------------------------------------------------------------


def _make_client(
    meetings: list[dict],
    sessions: list[dict],
) -> MagicMock:
    """Return a fake httpx.AsyncClient that serves predefined payloads."""

    async def get(path: str, *, params: dict | None = None) -> MagicMock:
        resp = MagicMock(spec=httpx.Response)
        resp.raise_for_status.return_value = None
        resp.json.return_value = meetings if "meetings" in path else sessions
        return resp

    client = MagicMock(spec=httpx.AsyncClient)
    client.get = get
    return client


def _make_error_client(status_code: int) -> MagicMock:
    """Return a fake client whose get() raises HTTPStatusError."""

    async def get(path: str, *, params: dict | None = None) -> MagicMock:
        request = httpx.Request("GET", f"https://api.openf1.org/v1{path}")
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
# Helper: module-level pure functions
# ---------------------------------------------------------------------------


class TestResolveTimezone:
    def test_known_circuit_returns_iana_timezone(self) -> None:
        assert _resolve_timezone("Sakhir") == "Asia/Bahrain"
        assert _resolve_timezone("Albert Park") == "Australia/Melbourne"
        assert _resolve_timezone("Monaco") == "Europe/Monaco"
        assert _resolve_timezone("Silverstone") == "Europe/London"

    def test_unknown_circuit_falls_back_to_utc(self) -> None:
        assert _resolve_timezone("Unknown Circuit") == "UTC"
        assert _resolve_timezone("") == "UTC"


class TestParseSessionType:
    @pytest.mark.parametrize(
        ("session_name", "expected"),
        [
            ("Practice 1", SessionType.FP1),
            ("Practice 2", SessionType.FP2),
            ("Practice 3", SessionType.FP3),
            ("Qualifying", SessionType.QUALIFYING),
            ("Sprint Qualifying", SessionType.SPRINT_QUALIFYING),
            ("Sprint Shootout", SessionType.SPRINT_QUALIFYING),
            ("Sprint", SessionType.SPRINT),
            ("Race", SessionType.RACE),
        ],
    )
    def test_known_names(self, session_name: str, expected: SessionType) -> None:
        assert _parse_session_type(session_name) == expected

    def test_unknown_name_falls_back_to_free_practice(self) -> None:
        assert _parse_session_type("Super Sunday") == SessionType.FREE_PRACTICE


class TestBuildCircuit:
    def test_fields_mapped_correctly(self) -> None:
        circuit = _build_circuit(_BAHRAIN_MEETING)
        assert circuit.id == "openf1-circuit-1"
        assert circuit.name == "Sakhir"
        assert circuit.city == "Sakhir"
        assert circuit.country == "Bahrain"
        assert circuit.timezone == "Asia/Bahrain"

    def test_unknown_circuit_gets_utc_timezone(self) -> None:
        meeting = {**_BAHRAIN_MEETING, "circuit_short_name": "Nowhere", "circuit_key": 999}
        circuit = _build_circuit(meeting)
        assert circuit.timezone == "UTC"


class TestBuildSession:
    def test_complete_session_is_built(self) -> None:
        session = _build_session(_BAHRAIN_RACE)
        assert session is not None
        assert session.type == SessionType.RACE
        assert session.title == "Race"
        assert session.start_datetime.tzinfo is not None
        assert session.end_datetime.tzinfo is not None

    def test_missing_date_end_returns_none(self) -> None:
        raw = {**_BAHRAIN_RACE, "date_end": None}
        assert _build_session(raw) is None

    def test_missing_date_start_returns_none(self) -> None:
        raw = {**_BAHRAIN_RACE, "date_start": None}
        assert _build_session(raw) is None

    def test_absent_date_end_key_returns_none(self) -> None:
        raw = {k: v for k, v in _BAHRAIN_RACE.items() if k != "date_end"}
        assert _build_session(raw) is None

    def test_invalid_date_format_returns_none(self) -> None:
        raw = {**_BAHRAIN_RACE, "date_start": "not-a-date"}
        assert _build_session(raw) is None

    def test_end_equal_to_start_returns_none(self) -> None:
        raw = {**_BAHRAIN_RACE, "date_end": _BAHRAIN_RACE["date_start"]}
        assert _build_session(raw) is None

    def test_end_before_start_returns_none(self) -> None:
        raw = {**_BAHRAIN_RACE, "date_end": "2024-03-01T14:00:00+00:00"}
        assert _build_session(raw) is None


# ---------------------------------------------------------------------------
# Integration: OpenF1Source.get_season (all HTTP mocked)
# ---------------------------------------------------------------------------


class TestGetSeasonHappyPath:
    async def test_one_meeting_produces_one_event(self) -> None:
        client = _make_client(
            meetings=[_BAHRAIN_MEETING],
            sessions=[_BAHRAIN_RACE],
        )
        events = await OpenF1Source(client).get_season(2024)
        assert len(events) == 1

    async def test_empty_meetings_returns_empty_list(self) -> None:
        client = _make_client(meetings=[], sessions=[])
        events = await OpenF1Source(client).get_season(2024)
        assert events == []

    async def test_sessions_grouped_by_meeting(self) -> None:
        client = _make_client(
            meetings=[_BAHRAIN_MEETING],
            sessions=[_BAHRAIN_FP1, _BAHRAIN_QUALIFYING, _BAHRAIN_RACE],
        )
        events = await OpenF1Source(client).get_season(2024)
        assert len(events[0].sessions) == 3

    async def test_sessions_of_other_meeting_not_attached(self) -> None:
        aus_race = {**_BAHRAIN_RACE, "meeting_key": 1230, "session_key": 9999}
        client = _make_client(
            meetings=[_BAHRAIN_MEETING],
            sessions=[_BAHRAIN_RACE, aus_race],
        )
        events = await OpenF1Source(client).get_season(2024)
        # Only the Bahrain race should be attached
        assert len(events[0].sessions) == 1

    async def test_two_meetings_produce_two_events(self) -> None:
        client = _make_client(
            meetings=[_BAHRAIN_MEETING, _AUSTRALIA_MEETING],
            sessions=[],
        )
        events = await OpenF1Source(client).get_season(2024)
        assert len(events) == 2

    async def test_meetings_sorted_chronologically(self) -> None:
        # Australia meeting has an earlier date_start than Bahrain in 2024 season
        # (note: in real life Bahrain is R1 — this tests date-based sorting)
        client = _make_client(
            meetings=[_AUSTRALIA_MEETING, _BAHRAIN_MEETING],  # reversed order in response
            sessions=[],
        )
        events = await OpenF1Source(client).get_season(2024)
        # Bahrain 2024-02-29 < Australia 2024-03-14
        assert events[0].name == "Bahrain Grand Prix"
        assert events[1].name == "Australian Grand Prix"

    async def test_round_number_reflects_chronological_order(self) -> None:
        client = _make_client(
            meetings=[_AUSTRALIA_MEETING, _BAHRAIN_MEETING],
            sessions=[],
        )
        events = await OpenF1Source(client).get_season(2024)
        bahrain = next(e for e in events if "Bahrain" in e.name)
        australia = next(e for e in events if "Australian" in e.name)
        assert bahrain.round < australia.round

    async def test_incomplete_sessions_skipped(self) -> None:
        no_end = {k: v for k, v in _BAHRAIN_RACE.items() if k != "date_end"}
        client = _make_client(
            meetings=[_BAHRAIN_MEETING],
            sessions=[no_end, _BAHRAIN_FP1],
        )
        events = await OpenF1Source(client).get_season(2024)
        assert len(events[0].sessions) == 1  # only FP1 is complete


class TestGetSeasonEventFields:
    async def test_event_name_matches_meeting_name(self) -> None:
        client = _make_client(meetings=[_BAHRAIN_MEETING], sessions=[])
        events = await OpenF1Source(client).get_season(2024)
        assert events[0].name == "Bahrain Grand Prix"

    async def test_event_season_matches_year(self) -> None:
        client = _make_client(meetings=[_BAHRAIN_MEETING], sessions=[])
        events = await OpenF1Source(client).get_season(2024)
        assert events[0].season == 2024

    async def test_event_uid_contains_meeting_key(self) -> None:
        client = _make_client(meetings=[_BAHRAIN_MEETING], sessions=[])
        events = await OpenF1Source(client).get_season(2024)
        assert "1229" in events[0].event_uid

    async def test_event_uid_is_stable_across_calls(self) -> None:
        client1 = _make_client(meetings=[_BAHRAIN_MEETING], sessions=[])
        client2 = _make_client(meetings=[_BAHRAIN_MEETING], sessions=[])
        e1 = await OpenF1Source(client1).get_season(2024)
        e2 = await OpenF1Source(client2).get_season(2024)
        assert e1[0].event_uid == e2[0].event_uid

    async def test_championship_is_formula1(self) -> None:
        client = _make_client(meetings=[_BAHRAIN_MEETING], sessions=[])
        events = await OpenF1Source(client).get_season(2024)
        champ = events[0].championship
        assert champ.category == ChampionshipCategory.SINGLE_SEATER
        assert "Formula 1" in champ.name

    async def test_championship_id_contains_year(self) -> None:
        client = _make_client(meetings=[_BAHRAIN_MEETING], sessions=[])
        events = await OpenF1Source(client).get_season(2024)
        assert "2024" in events[0].championship.id


class TestGetSeasonSessionFields:
    async def test_session_type_mapped_correctly(self) -> None:
        client = _make_client(
            meetings=[_BAHRAIN_MEETING],
            sessions=[_BAHRAIN_FP1, _BAHRAIN_QUALIFYING, _BAHRAIN_RACE],
        )
        events = await OpenF1Source(client).get_season(2024)
        types = {s.type for s in events[0].sessions}
        assert SessionType.FP1 in types
        assert SessionType.QUALIFYING in types
        assert SessionType.RACE in types

    async def test_session_title_matches_session_name(self) -> None:
        client = _make_client(meetings=[_BAHRAIN_MEETING], sessions=[_BAHRAIN_RACE])
        events = await OpenF1Source(client).get_season(2024)
        assert events[0].sessions[0].title == "Race"

    async def test_datetimes_are_timezone_aware(self) -> None:
        client = _make_client(meetings=[_BAHRAIN_MEETING], sessions=[_BAHRAIN_RACE])
        events = await OpenF1Source(client).get_season(2024)
        session = events[0].sessions[0]
        assert session.start_datetime.tzinfo is not None
        assert session.end_datetime.tzinfo is not None

    async def test_sessions_ordered_by_start_datetime(self) -> None:
        client = _make_client(
            meetings=[_BAHRAIN_MEETING],
            sessions=[_BAHRAIN_RACE, _BAHRAIN_FP1, _BAHRAIN_QUALIFYING],  # shuffled
        )
        events = await OpenF1Source(client).get_season(2024)
        starts = [s.start_datetime for s in events[0].sessions]
        assert starts == sorted(starts)


class TestGetSeasonCircuitFields:
    async def test_circuit_name_from_circuit_short_name(self) -> None:
        client = _make_client(meetings=[_BAHRAIN_MEETING], sessions=[])
        events = await OpenF1Source(client).get_season(2024)
        assert events[0].circuit.name == "Sakhir"

    async def test_circuit_country_from_meeting(self) -> None:
        client = _make_client(meetings=[_BAHRAIN_MEETING], sessions=[])
        events = await OpenF1Source(client).get_season(2024)
        assert events[0].circuit.country == "Bahrain"

    async def test_circuit_timezone_resolved(self) -> None:
        client = _make_client(meetings=[_BAHRAIN_MEETING], sessions=[])
        events = await OpenF1Source(client).get_season(2024)
        assert events[0].circuit.timezone == "Asia/Bahrain"

    async def test_unknown_circuit_timezone_is_utc(self) -> None:
        unknown = {**_BAHRAIN_MEETING, "circuit_short_name": "Unknown"}
        client = _make_client(meetings=[unknown], sessions=[])
        events = await OpenF1Source(client).get_season(2024)
        assert events[0].circuit.timezone == "UTC"


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestGetSeasonErrors:
    async def test_http_404_propagates(self) -> None:
        client = _make_error_client(404)
        with pytest.raises(httpx.HTTPStatusError):
            await OpenF1Source(client).get_season(2024)

    async def test_http_500_propagates(self) -> None:
        client = _make_error_client(500)
        with pytest.raises(httpx.HTTPStatusError):
            await OpenF1Source(client).get_season(2024)

    async def test_timeout_propagates(self) -> None:
        client = _make_timeout_client()
        with pytest.raises(httpx.TimeoutException):
            await OpenF1Source(client).get_season(2024)
