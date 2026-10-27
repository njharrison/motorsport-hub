"""Abstract base for the MotoGP-family classes, sourced from Dorna's official API.

MotoGP, Moto2 and Moto3 all race on the same Grand Prix weekend, at the same
circuit, and are exposed by the same official, unauthenticated, JSON REST API
run by Dorna Sports — confirmed empirically (Sprint 38) by fetching the
season endpoint directly: ``https://api.pulselive.motogp.com/motogp/v1/events
?seasonYear={year}`` returns every event of the season in one response, and
each Grand Prix event (``kind == "GP"``, as opposed to ``"TEST"``/``"MEDIA"``)
already embeds a ``broadcasts`` array covering every session of every class at
that round, each tagged with its own ``category.acronym`` (``MGP``/``MT2``/
``MT3``) and a real ``date_start``/``date_end`` pair. No scraping, no
JSON-LD, no HTML tables needed — this is the "API officielle" tier the
project's sourcing policy asks to prefer whenever it exists, and one HTTP
request per season covers all three classes (`HttpCache` naturally
deduplicates the three providers' identical requests for the same season).

Two data-shape quirks handled generically here, not per-class:
  - Each class runs three PRACTICE-kind sessions per weekend, but only two
    carry an explicit number in their ``shortname`` (``FP1``/``FP2``) — the
    middle one is simply called ``PR`` ("Practice"). Rather than trust the
    embedded label, the three PRACTICE-kind broadcasts for a class are sorted
    chronologically and assigned ``FP1``/``FP2``/``FP3`` by slot order (the
    ``Session.title`` still carries the broadcast's own name, so the
    mismatch between "my FP3" and the source's "FP2" is never hidden from
    whoever reads the exported calendar).
  - Qualifying runs as two back-to-back segments (``Q1``, ``Q2``) per class.
    Both map to ``SessionType.QUALIFYING`` and would collide on ICS UID
    (``{event_uid}-{session.type}``) — merged into a single Session spanning
    Q1's start to Q2's real end (both timestamps are given by the source,
    unlike the ACO/SRO scrapers, which had to invent a duration).
  - ``RACE``-kind broadcasts (the Sprint and the Grand Prix race itself)
    always report ``date_start == date_end`` — the source never predicts a
    finish time. Duration is a fixed, documented default per class/format
    (``_RACE_DURATION_MINUTES``), the same kind of approximation already
    used by ``JolpicaSource``/``OpenF1Source`` for their own default
    durations.

``WARM_UP`` (MotoGP-only, 10 minutes, no equivalent SessionType) and
``PRESS``-kind broadcasts (photo calls, press conferences, parades) are
excluded entirely — consistent with every other provider in this project
only covering championship-relevant track sessions.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import UTC, datetime, timedelta
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

_TIMEOUT = 10.0
_EVENTS_URL = "https://api.pulselive.motogp.com/motogp/v1/events"

# Non-championship entries in the season's event list (pre-season tests,
# team launches, media days) — only "GP" rounds are real championship events.
_GP_KIND = "GP"

# Broadcast kinds that are never track sessions.
_EXCLUDED_BROADCAST_KINDS = {"PRESS", "WARM_UP"}

_DEFAULT_FP_MINUTES = 45
_DEFAULT_QUALIFYING_MINUTES = 15


def _classify_broadcast(kind: str, shortname: str) -> str | None:
    """Return "practice" / "qualifying" / "sprint" / "race", or None to skip."""
    if kind in _EXCLUDED_BROADCAST_KINDS:
        return None
    if kind == "PRACTICE":
        return "practice"
    if kind == "QUALIFYING":
        return "qualifying"
    if kind == "RACE":
        return "sprint" if shortname == "SPR" else "race"
    return None


class PulseliveGpSource(JsonDataSource, ABC):
    """Abstract base for MotoGP/Moto2/Moto3, scoped to one ``category`` acronym.

    Subclasses declare only class-specific configuration; all HTTP, cache,
    JSON parsing and session-mapping logic is provided here.

    Args:
        client: Optional httpx.AsyncClient for injection (tests). When
            omitted, a default client with a 10-second timeout is created.
            When provided, cache is disabled by default (test mode).
        cache: Optional HttpCache. Defaults to HttpCache() when no custom
            client is given. Pass None to disable.
        refresh: When True, ignore cached data and re-fetch from the source.
    """

    @property
    @abstractmethod
    def _series_key(self) -> str:
        """ICS UID prefix and circuit-id prefix, e.g. 'motogp', 'moto2'."""

    @property
    @abstractmethod
    def _category_acronym(self) -> str:
        """Dorna category acronym to filter broadcasts by: 'MGP'/'MT2'/'MT3'."""

    @property
    @abstractmethod
    def _race_duration_minutes(self) -> int:
        """Default RACE duration — the source never reports a real finish time."""

    @abstractmethod
    def _make_championship(self, year: int) -> Championship:
        """Return the Championship object for this class and year."""

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

    # ------------------------------------------------------------------
    # JsonDataSource contract
    # ------------------------------------------------------------------

    async def fetch_json(self, url: str, params: dict[str, Any]) -> list[Any] | dict[str, Any]:
        """Fetch JSON from *url*; uses cache when available."""

        async def _do_fetch(_url: str, _params: dict[str, Any]) -> list[Any] | dict[str, Any]:
            response = await self._client.get(_url, params=_params)
            response.raise_for_status()
            return response.json()  # type: ignore[no-any-return]

        if self._cache is not None:
            return await self._cache.get_json(url, params, _do_fetch, refresh=self._refresh)
        return await _do_fetch(url, params)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get_season(self, year: int) -> list[Event]:
        raw = await self.fetch_json(_EVENTS_URL, {"seasonYear": year})
        events_data: list[dict[str, Any]] = raw if isinstance(raw, list) else []
        gp_events = sorted(
            (e for e in events_data if e.get("kind") == _GP_KIND),
            key=lambda e: e.get("date_start") or "",
        )

        championship = self._make_championship(year)
        events: list[Event] = []
        for round_number, event_data in enumerate(gp_events, start=1):
            sessions = self._build_sessions(event_data)
            if not sessions:
                continue
            events.append(self._build_event(championship, event_data, round_number, year, sessions))
        return events

    # ------------------------------------------------------------------
    # Internals — event/circuit construction
    # ------------------------------------------------------------------

    def _build_event(
        self,
        championship: Championship,
        event_data: dict[str, Any],
        round_number: int,
        year: int,
        sessions: list[Session],
    ) -> Event:
        circuit = self._build_circuit(event_data)
        name = (event_data.get("name") or "").strip() or event_data.get("shortname", "")
        return Event(
            championship=championship,
            season=year,
            round=round_number,
            name=name,
            circuit=circuit,
            sessions=tuple(sessions),
            event_uid=(
                f"{self._series_key}-{year}-{event_data.get('id', round_number)}"
                "@motorsport-calendar"
            ),
        )

    def _build_circuit(self, event_data: dict[str, Any]) -> Circuit:
        circuit_data: dict[str, Any] = event_data.get("circuit") or {}
        name: str = circuit_data.get("name") or event_data.get("shortname", "Unknown")
        city: str = (circuit_data.get("city") or "").strip() or name
        country: str = circuit_data.get("country") or "Unknown"
        raw_tz: str = event_data.get("time_zone") or ""
        timezone = raw_tz.title() if raw_tz else "UTC"
        circuit_id = circuit_data.get("id") or name
        return Circuit(
            id=f"{self._series_key}-{circuit_id}",
            name=name,
            city=city,
            country=country,
            timezone=timezone,
        )

    # ------------------------------------------------------------------
    # Internals — session construction
    # ------------------------------------------------------------------

    def _build_sessions(self, event_data: dict[str, Any]) -> list[Session]:
        broadcasts: list[dict[str, Any]] = event_data.get("broadcasts") or []

        by_class: dict[str, list[dict[str, Any]]] = {
            "practice": [],
            "qualifying": [],
            "sprint": [],
            "race": [],
        }
        for broadcast in broadcasts:
            category = broadcast.get("category") or {}
            if category.get("acronym") != self._category_acronym:
                continue
            start = self._parse_datetime(broadcast.get("date_start"))
            if start is None:
                continue
            kind = _classify_broadcast(broadcast.get("kind", ""), broadcast.get("shortname", ""))
            if kind is None:
                continue
            by_class[kind].append(broadcast)

        sessions: list[Session] = []
        sessions.extend(self._build_practice_sessions(by_class["practice"]))
        sessions.extend(self._build_qualifying_sessions(by_class["qualifying"]))
        if by_class["sprint"]:
            sessions.append(
                self._build_single_session(
                    by_class["sprint"][0], SessionType.SPRINT, self._sprint_duration_minutes
                )
            )
        if by_class["race"]:
            sessions.append(
                self._build_single_session(
                    by_class["race"][0], SessionType.RACE, self._race_duration_minutes
                )
            )

        sessions.sort(key=lambda s: s.start_datetime)
        return sessions

    @property
    def _sprint_duration_minutes(self) -> int:
        """Default SPRINT duration — MotoGP-only, shorter than the full race."""
        return 30

    def _build_practice_sessions(self, entries: list[dict[str, Any]]) -> list[Session]:
        if not entries:
            return []
        entries = sorted(entries, key=lambda e: e["date_start"])
        fp_types = [SessionType.FP1, SessionType.FP2, SessionType.FP3]
        sessions: list[Session] = []
        for i, session_type in enumerate(fp_types):
            if i >= len(entries):
                break
            if i == 2 and len(entries) > 3:
                overflow = entries[i:]
                start = self._parse_datetime(overflow[0]["date_start"])
                end = self._parse_datetime(overflow[-1]["date_end"]) or (
                    start + timedelta(minutes=_DEFAULT_FP_MINUTES) if start else None
                )
                title = overflow[0].get("name", "Practice")
            else:
                entry = entries[i]
                start = self._parse_datetime(entry["date_start"])
                end = self._parse_datetime(entry.get("date_end")) or (
                    start + timedelta(minutes=_DEFAULT_FP_MINUTES) if start else None
                )
                title = entry.get("name", "Practice")
            if start is None or end is None or end <= start:
                end = start + timedelta(minutes=_DEFAULT_FP_MINUTES) if start else end
            if start is None or end is None:
                continue
            sessions.append(
                Session(type=session_type, start_datetime=start, end_datetime=end, title=title)
            )
        return sessions

    def _build_qualifying_sessions(self, entries: list[dict[str, Any]]) -> list[Session]:
        if not entries:
            return []
        entries = sorted(entries, key=lambda e: e["date_start"])
        first_start = self._parse_datetime(entries[0]["date_start"])
        last_end = self._parse_datetime(entries[-1].get("date_end")) or self._parse_datetime(
            entries[-1]["date_start"]
        )
        if first_start is None or last_end is None:
            return []
        if last_end <= first_start:
            last_end = first_start + timedelta(minutes=_DEFAULT_QUALIFYING_MINUTES)
        title = entries[0].get("name", "Qualifying") if len(entries) == 1 else "Qualifying"
        return [
            Session(
                type=SessionType.QUALIFYING,
                start_datetime=first_start,
                end_datetime=last_end,
                title=title,
            )
        ]

    def _build_single_session(
        self, entry: dict[str, Any], session_type: SessionType, default_minutes: int
    ) -> Session:
        start = self._parse_datetime(entry["date_start"])
        end = self._parse_datetime(entry.get("date_end"))
        assert start is not None  # filtered upstream in _build_sessions
        if end is None or end <= start:
            end = start + timedelta(minutes=default_minutes)
        title = entry.get("name", session_type.value.title())
        return Session(type=session_type, start_datetime=start, end_datetime=end, title=title)

    @staticmethod
    def _parse_datetime(value: str | None) -> datetime | None:
        """Parse an ISO 8601 timestamp and normalise it to UTC.

        The source reports each timestamp with the circuit's local UTC
        offset (e.g. ``+07:00``) rather than UTC itself. Every other
        provider in this project stores session times in UTC — normalising
        here keeps ``IcsExporter`` emitting a plain ``Z``-suffixed
        ``DTSTART`` instead of a synthetic ``TZID="UTC+07:00"`` that has no
        accompanying ``VTIMEZONE`` block.
        """
        if not value:
            return None
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            return None
        return parsed.astimezone(UTC)
