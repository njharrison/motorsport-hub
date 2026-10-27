"""JolpicaSource — fetches F1 season data from the Jolpica API (Ergast successor, 1950+)."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, cast

import httpx

from motorsport_calendar.cache import HttpCache
from motorsport_calendar.models import (
    Championship,
    ChampionshipCategory,
    Circuit,
    Event,
    Session,
    SessionType,
)
from motorsport_calendar.providers.formula1.source import Formula1Source

_BASE_URL = "http://api.jolpi.ca/ergast/f1"
_TIMEOUT = 10.0

# (Race-object field key, SessionType, session duration in minutes)
# Race is handled separately via top-level "date"/"time" keys.
_SESSION_FIELDS: list[tuple[str, SessionType, int]] = [
    ("FirstPractice", SessionType.FP1, 60),
    ("SecondPractice", SessionType.FP2, 60),
    ("ThirdPractice", SessionType.FP3, 60),
    ("Qualifying", SessionType.QUALIFYING, 60),
    ("SprintQualifying", SessionType.SPRINT_QUALIFYING, 45),
    ("Sprint", SessionType.SPRINT, 35),
]

_SESSION_TITLES: dict[SessionType, str] = {
    SessionType.FP1: "Practice 1",
    SessionType.FP2: "Practice 2",
    SessionType.FP3: "Practice 3",
    SessionType.QUALIFYING: "Qualifying",
    SessionType.SPRINT_QUALIFYING: "Sprint Qualifying",
    SessionType.SPRINT: "Sprint",
    SessionType.RACE: "Race",
}

# Jolpica circuitId (snake_case) → IANA timezone
_CIRCUIT_TZ_MAP: dict[str, str] = {
    "albert_park": "Australia/Melbourne",
    "americas": "America/Chicago",
    "bahrain": "Asia/Bahrain",
    "bahrain_outer": "Asia/Bahrain",
    "baku": "Asia/Baku",
    "catalunya": "Europe/Madrid",
    "hungaroring": "Europe/Budapest",
    "imola": "Europe/Rome",
    "indianapolis": "America/Indiana/Indianapolis",
    "interlagos": "America/Sao_Paulo",
    "istanbul": "Europe/Istanbul",
    "jeddah": "Asia/Riyadh",
    "las_vegas": "America/Los_Angeles",
    "losail": "Asia/Qatar",
    "marina_bay": "Asia/Singapore",
    "miami": "America/New_York",
    "monaco": "Europe/Monaco",
    "monza": "Europe/Rome",
    "mugello": "Europe/Rome",
    "nurburgring": "Europe/Berlin",
    "portimao": "Europe/Lisbon",
    "red_bull_ring": "Europe/Vienna",
    "ricard": "Europe/Paris",
    "rodriguez": "America/Mexico_City",
    "shanghai": "Asia/Shanghai",
    "silverstone": "Europe/London",
    "sochi": "Europe/Moscow",
    "spa": "Europe/Brussels",
    "suzuka": "Asia/Tokyo",
    "valencia": "Europe/Madrid",
    "villeneuve": "America/Montreal",
    "yas_marina": "Asia/Dubai",
    "yeongam": "Asia/Seoul",
    "zandvoort": "Europe/Amsterdam",
    "zhuhai": "Asia/Shanghai",
}

_RACE_DURATION_MINUTES = 130


class JolpicaSource(Formula1Source):
    """Fetches F1 season data from the Jolpica API (Ergast successor, 1950+).

    Makes a single request per season:
    ``GET http://api.jolpi.ca/ergast/f1/{year}/races.json?limit=100``

    Session end times are inferred from session type (Jolpica does not
    provide them). Results are cached on disk via ``HttpCache``.
    Pass ``refresh=True`` to bypass the cache.

    Args:
        client: Optional ``httpx.AsyncClient`` to inject (useful in tests).
                When omitted a default client targeting Jolpica with a
                10-second timeout is created.
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
        races_raw = await self._get_json(year)
        championship = _make_championship(year)
        return [_build_event(championship, race) for race in races_raw]

    async def _get_json(self, year: int) -> list[dict[str, Any]]:
        path = f"/{year}/races.json"
        url = f"{_BASE_URL}{path}"
        params: dict[str, int] = {"limit": 100}

        async def _do_fetch(_url: str, _params: dict[str, Any]) -> dict[str, Any]:
            response = await self._client.get(path, params=_params)
            response.raise_for_status()
            return response.json()  # type: ignore[no-any-return]

        if self._cache is not None:
            raw = await self._cache.get_json(url, params, _do_fetch, refresh=self._refresh)
        else:
            raw = await _do_fetch(url, params)

        # L'API Jolpica renvoie toujours un objet JSON (jamais une liste) pour cet
        # endpoint — HttpCache.get_json() est générique (list | dict) côté signature.
        raw = cast(dict[str, Any], raw)
        races: list[dict[str, Any]] = raw["MRData"]["RaceTable"]["Races"]
        return races


# ---------------------------------------------------------------------------
# Pure mapping helpers (module-level, no I/O)
# ---------------------------------------------------------------------------


def _make_championship(year: int) -> Championship:
    return Championship(
        id=f"formula1-{year}",
        name="Formula 1 World Championship",
        category=ChampionshipCategory.SINGLE_SEATER,
    )


def _resolve_timezone(circuit_id: str) -> str:
    return _CIRCUIT_TZ_MAP.get(circuit_id, "UTC")


def _build_circuit(race: dict[str, Any]) -> Circuit:
    circuit_data: dict[str, Any] = race["Circuit"]
    circuit_id: str = circuit_data["circuitId"]
    location: dict[str, Any] = circuit_data["Location"]
    return Circuit(
        id=f"jolpica-{circuit_id}",
        name=circuit_data["circuitName"],
        city=location["locality"],
        country=location["country"],
        timezone=_resolve_timezone(circuit_id),
    )


def _build_session(
    data: dict[str, str | None],
    session_type: SessionType,
    duration_minutes: int,
) -> Session | None:
    """Build a Session from a Jolpica date/time dict, or return None if data is incomplete."""
    date_str = data.get("date")
    time_str = data.get("time")

    if not date_str or not time_str:
        return None

    try:
        start = datetime.fromisoformat(f"{date_str}T{time_str}")
    except ValueError:
        return None

    if start.tzinfo is None:
        return None

    end = start + timedelta(minutes=duration_minutes)

    return Session(
        type=session_type,
        start_datetime=start,
        end_datetime=end,
        title=_SESSION_TITLES[session_type],
    )


def _build_event(championship: Championship, race: dict[str, Any]) -> Event:
    circuit = _build_circuit(race)
    sessions: list[Session] = []

    for field, session_type, duration in _SESSION_FIELDS:
        if field in race:
            session = _build_session(race[field], session_type, duration)
            if session is not None:
                sessions.append(session)

    # Race time is at the top level of the race object; fall back to noon UTC for old races.
    race_time: str = race.get("time") or "12:00:00Z"
    race_session = _build_session(
        {"date": race.get("date"), "time": race_time},
        SessionType.RACE,
        _RACE_DURATION_MINUTES,
    )
    if race_session is not None:
        sessions.append(race_session)

    sessions.sort(key=lambda s: s.start_datetime)

    return Event(
        championship=championship,
        season=int(race["season"]),
        round=int(race["round"]),
        name=race["raceName"],
        circuit=circuit,
        sessions=tuple(sessions),
        event_uid=f"jolpica-{race['season']}-{race['round']}@motorsport-calendar",
    )
