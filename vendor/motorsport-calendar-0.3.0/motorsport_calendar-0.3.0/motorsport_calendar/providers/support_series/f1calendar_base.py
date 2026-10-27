"""Abstract base for all series sourced from the f1calendar open dataset (MIT).

Any support-series provider that uses https://github.com/sportstimes/f1 as its
data source should subclass F1CalendarBaseSource and declare four series-specific
configuration properties. All HTTP, cache, and JSON-to-model logic is provided here.

URL pattern: https://raw.githubusercontent.com/sportstimes/f1/main/_db/{series_key}/{year}.json
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any

import httpx

from motorsport_calendar.cache import HttpCache
from motorsport_calendar.core.datasource import JsonDataSource
from motorsport_calendar.models import (
    Championship,
    Circuit,
    Event,
    Session,
    SessionType,
)

_BASE_URL = "https://raw.githubusercontent.com/sportstimes/f1/main/_db"
_TIMEOUT = 10.0


def _build_session(
    timestamp: str,
    session_type: SessionType,
    duration_minutes: int,
    title: str,
) -> Session | None:
    """Build a Session from an ISO 8601 UTC timestamp, or return None if invalid.

    Returns None for missing, unparseable, or timezone-naive timestamps.
    """
    try:
        start = datetime.fromisoformat(timestamp)
    except (ValueError, TypeError):
        return None
    if start.tzinfo is None:
        return None
    return Session(
        type=session_type,
        start_datetime=start,
        end_datetime=start + timedelta(minutes=duration_minutes),
        title=title,
    )


class F1CalendarBaseSource(JsonDataSource, ABC):
    """Abstract base for f1calendar-sourced support series (F2, F3, Academy, Supercup).

    Subclasses declare four pieces of series-specific configuration; all HTTP,
    cache, and mapping logic is inherited from here.

    Args:
        client: Optional httpx.AsyncClient for injection (tests). When omitted,
                a default client with a 10-second timeout is created.
                When provided, cache is disabled by default (test mode).
        cache: Optional HttpCache. Defaults to HttpCache() when no custom client
               is given. Pass None to disable.
        refresh: When True, ignore cached data and re-fetch from the source.

    Raises:
        httpx.HTTPStatusError: Propagated on HTTP 4xx / 5xx responses.
        httpx.TimeoutException: Propagated when the request exceeds 10 seconds.
    """

    @property
    @abstractmethod
    def _series_key(self) -> str:
        """URL path segment and ICS UID prefix, e.g. 'f2', 'f3'."""

    @property
    @abstractmethod
    def _session_map(self) -> dict[str, tuple[SessionType, int, str]]:
        """JSON session key → (SessionType, duration_minutes, display_title)."""

    @property
    @abstractmethod
    def _circuit_data(self) -> dict[str, tuple[str, str]]:
        """Circuit slug → (country, IANA timezone)."""

    @abstractmethod
    def _make_championship(self, year: int) -> Championship:
        """Return the Championship object for this series and year."""

    def __init__(
        self,
        client: httpx.AsyncClient | None = None,
        cache: HttpCache | None = None,
        *,
        refresh: bool = False,
    ) -> None:
        self._client = client or httpx.AsyncClient(timeout=_TIMEOUT)
        self._cache = cache if cache is not None else (HttpCache() if client is None else None)
        self._refresh = refresh

    async def get_season(self, year: int) -> list[Event]:
        url = f"{_BASE_URL}/{self._series_key}/{year}.json"
        raw = await self.fetch_json(url, {})
        championship = self._make_championship(year)
        return [
            self._build_event(championship, event_data, year)
            for event_data in raw.get("races", [])  # type: ignore[union-attr]
        ]

    async def fetch_json(self, url: str, params: dict[str, Any]) -> list[Any] | dict[str, Any]:
        """Fetch JSON from *url*; uses cache when available."""

        async def _do_fetch(_url: str, _params: dict[str, Any]) -> dict[str, Any]:
            response = await self._client.get(url, params=_params)
            response.raise_for_status()
            return response.json()  # type: ignore[no-any-return]

        if self._cache is not None:
            return await self._cache.get_json(url, params, _do_fetch, refresh=self._refresh)
        return await _do_fetch(url, params)

    def _resolve_circuit_data(self, slug: str) -> tuple[str, str]:
        return self._circuit_data.get(slug, ("Unknown", "UTC"))

    def _build_circuit(self, event_data: dict[str, Any]) -> Circuit:
        slug: str = event_data.get("slug", "")
        country, timezone = self._resolve_circuit_data(slug)
        return Circuit(
            id=f"f1calendar-{self._series_key}-{slug}",
            name=event_data.get("name", slug),
            city=event_data.get("location", slug),
            country=country,
            timezone=timezone,
        )

    def _build_event(
        self, championship: Championship, event_data: dict[str, Any], year: int
    ) -> Event:
        circuit = self._build_circuit(event_data)
        sessions: list[Session] = []
        raw_sessions: dict[str, Any] = event_data.get("sessions", {})
        for key, (session_type, duration, title) in self._session_map.items():
            if key in raw_sessions:
                session = _build_session(raw_sessions[key], session_type, duration, title)
                if session is not None:
                    sessions.append(session)
        sessions.sort(key=lambda s: s.start_datetime)
        round_number: int = int(event_data.get("round", 0))
        return Event(
            championship=championship,
            season=year,
            round=round_number,
            name=event_data.get("name", ""),
            circuit=circuit,
            sessions=tuple(sessions),
            event_uid=f"f1calendar-{self._series_key}-{year}-{round_number}@motorsport-calendar",
        )
