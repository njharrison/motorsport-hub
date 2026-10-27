"""OpenF1Source — fetches F1 season data from the OpenF1 REST API (2023+)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx

from motorsport_calendar.cache import HttpCache
from motorsport_calendar.core.datasource import JsonDataSource
from motorsport_calendar.models import (
    Championship,
    ChampionshipCategory,
    Circuit,
    Event,
    Session,
    SessionType,
)
from motorsport_calendar.providers.formula1.source import Formula1Source

_BASE_URL = "https://api.openf1.org/v1"
_TIMEOUT = 10.0

# OpenF1 session_name → our SessionType
# Sprint Shootout was renamed Sprint Qualifying starting 2024
_SESSION_TYPE_MAP: dict[str, SessionType] = {
    "Practice 1": SessionType.FP1,
    "Practice 2": SessionType.FP2,
    "Practice 3": SessionType.FP3,
    "Qualifying": SessionType.QUALIFYING,
    "Sprint Qualifying": SessionType.SPRINT_QUALIFYING,
    "Sprint Shootout": SessionType.SPRINT_QUALIFYING,
    "Sprint": SessionType.SPRINT,
    "Race": SessionType.RACE,
}

# OpenF1 circuit_short_name → IANA timezone
# Fallback: "UTC" (OpenF1 returns UTC datetimes regardless)
_CIRCUIT_TZ_MAP: dict[str, str] = {
    "Albert Park": "Australia/Melbourne",
    "Austin": "America/Chicago",
    "Baku": "Asia/Baku",
    "Barcelona": "Europe/Madrid",
    "Budapest": "Europe/Budapest",
    "Imola": "Europe/Rome",
    "Interlagos": "America/Sao_Paulo",
    "Jeddah": "Asia/Riyadh",
    "Las Vegas": "America/Los_Angeles",
    "Losail": "Asia/Qatar",
    "Lusail": "Asia/Qatar",
    "Mexico City": "America/Mexico_City",
    "Miami": "America/New_York",
    "Monaco": "Europe/Monaco",
    "Monza": "Europe/Rome",
    "Montreal": "America/Montreal",
    "Sakhir": "Asia/Bahrain",
    "Shanghai": "Asia/Shanghai",
    "Singapore": "Asia/Singapore",
    "Silverstone": "Europe/London",
    "Spa-Francorchamps": "Europe/Brussels",
    "Spielberg": "Europe/Vienna",
    "Suzuka": "Asia/Tokyo",
    "Yas Marina": "Asia/Dubai",
    "Zandvoort": "Europe/Amsterdam",
}


class OpenF1Source(Formula1Source, JsonDataSource):
    """Fetches F1 season data from the OpenF1 REST API.

    Makes two requests per season: ``/meetings`` (race weekends) and
    ``/sessions`` (individual sessions). Sessions are grouped by
    ``meeting_key`` and attached to their parent Event.

    Results are transparently cached on disk (via ``HttpCache``) to avoid
    repeated network calls. Pass ``refresh=True`` to bypass the cache.

    Args:
        client: Optional ``httpx.AsyncClient`` to inject (useful in tests).
                When omitted a default client targeting ``api.openf1.org``
                with a 10-second timeout is created.
                When provided, cache is disabled by default (test mode).
        cache: Optional ``HttpCache`` instance. Defaults to ``HttpCache()``
               (``{cwd}/.cache/``, TTL 24 h) when no custom client is given.
               Pass ``None`` to disable caching explicitly.
        refresh: When True, ignore any cached data and re-fetch from the API.

    Raises:
        httpx.HTTPStatusError: Propagated on HTTP 4xx / 5xx responses.
        httpx.TimeoutException: Propagated when the API exceeds 10 seconds.
    """

    def __init__(
        self,
        client: httpx.AsyncClient | None = None,
        cache: HttpCache | None = None,
        *,
        refresh: bool = False,
    ) -> None:
        self._client = client or httpx.AsyncClient(base_url=_BASE_URL, timeout=_TIMEOUT)
        # When a custom client is injected (test mode), disable cache unless explicitly provided.
        self._cache = cache if cache is not None else (HttpCache() if client is None else None)
        self._refresh = refresh

    async def get_season(self, year: int) -> list[Event]:
        meetings_raw = await self._get_json("/meetings", {"year": year})
        sessions_raw = await self._get_json("/sessions", {"year": year})

        sessions_by_meeting: dict[int, list[dict[str, Any]]] = {}
        for raw in sessions_raw:
            sessions_by_meeting.setdefault(raw["meeting_key"], []).append(raw)

        championship = _make_championship(year)

        events: list[Event] = []
        for round_number, meeting in enumerate(
            sorted(meetings_raw, key=lambda m: m.get("date_start", "")),
            start=1,
        ):
            meeting_sessions = sessions_by_meeting.get(meeting["meeting_key"], [])
            events.append(_build_event(championship, meeting, meeting_sessions, round_number))

        return events

    # ------------------------------------------------------------------
    # JsonDataSource interface
    # ------------------------------------------------------------------

    async def fetch_json(self, url: str, params: dict[str, Any]) -> list[Any] | dict[str, Any]:
        """Fetch JSON from *url* with *params*, using cache when available."""
        path = url.removeprefix(_BASE_URL)

        async def _do_fetch(_url: str, _params: dict[str, Any]) -> list[Any] | dict[str, Any]:
            response = await self._client.get(path, params=_params)
            response.raise_for_status()
            return response.json()  # type: ignore[no-any-return]

        if self._cache is not None:
            return await self._cache.get_json(url, params, _do_fetch, refresh=self._refresh)

        return await _do_fetch(url, params)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _get_json(self, path: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        """Thin wrapper around fetch_json; kept for backward-compat with existing test mocks."""
        return await self.fetch_json(f"{_BASE_URL}{path}", params)  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Pure mapping helpers (module-level, no I/O)
# ---------------------------------------------------------------------------


def _make_championship(year: int) -> Championship:
    return Championship(
        id=f"formula1-{year}",
        name="Formula 1 World Championship",
        category=ChampionshipCategory.SINGLE_SEATER,
    )


def _resolve_timezone(circuit_short_name: str) -> str:
    return _CIRCUIT_TZ_MAP.get(circuit_short_name, "UTC")


def _parse_session_type(session_name: str) -> SessionType:
    return _SESSION_TYPE_MAP.get(session_name, SessionType.FREE_PRACTICE)


def _build_circuit(meeting: dict[str, Any]) -> Circuit:
    circuit_name: str = meeting["circuit_short_name"]
    return Circuit(
        id=f"openf1-circuit-{meeting['circuit_key']}",
        name=circuit_name,
        city=meeting["location"],
        country=meeting["country_name"],
        timezone=_resolve_timezone(circuit_name),
    )


def _build_session(raw: dict[str, Any]) -> Session | None:
    """Convert one OpenF1 session dict to a Session, or None if data is incomplete."""
    date_start: str | None = raw.get("date_start")
    date_end: str | None = raw.get("date_end")

    if not date_start or not date_end:
        return None

    try:
        start = datetime.fromisoformat(date_start)
        end = datetime.fromisoformat(date_end)
    except ValueError:
        return None

    # Both datetimes must be timezone-aware and end must be strictly after start
    if start.tzinfo is None or end.tzinfo is None or end <= start:
        return None

    return Session(
        type=_parse_session_type(raw["session_name"]),
        start_datetime=start,
        end_datetime=end,
        title=raw["session_name"],
    )


def _build_event(
    championship: Championship,
    meeting: dict[str, Any],
    sessions_raw: list[dict[str, Any]],
    round_number: int,
) -> Event:
    circuit = _build_circuit(meeting)

    sessions: list[Session] = []
    for raw in sorted(sessions_raw, key=lambda s: s.get("date_start", "")):
        session = _build_session(raw)
        if session is not None:
            sessions.append(session)

    return Event(
        championship=championship,
        season=meeting["year"],
        round=round_number,
        name=meeting["meeting_name"],
        circuit=circuit,
        sessions=tuple(sessions),
        event_uid=f"openf1-meeting-{meeting['meeting_key']}@motorsport-calendar",
    )
