"""Abstract base for ACO-organised endurance series scraped via schema.org JSON-LD.

WEC, ELMS and Michelin Le Mans Cup are all organised by the Automobile Club
de l'Ouest and run on the same web platform/CMS — confirmed empirically
(Sprint 35) by comparing raw HTML across the three sites, not assumed:
every race detail page (``/en/race/{slug}``) embeds a single
``<script type="application/ld+json">`` block describing a schema.org
``SportsEvent`` with a ``subEvent`` array, one entry per session, each with
an exact ISO 8601 timestamp (including UTC offset). The season list page
(``/en/season/{year}``) has no such structured data — it is scraped only
for the list of race slugs to visit.

This base class implements that two-step pipeline (season page -> race
slugs -> per-race JSON-LD) once; subclasses declare only series-specific
configuration (base URL, session-label -> SessionType mapping, circuit
timezones, event name prefix).

Two data-shape quirks handled generically here, not per-series:
  - Some rounds run *class-specific* qualifying as several back-to-back
    slots (e.g. "Qualifying session LMP2", "Qualifying session LMGT3" a few
    minutes apart) — these would all map to ``SessionType.QUALIFYING`` and
    collide on ICS UID (``{event_uid}-{session.type}``, see
    ``exporters/ics.py``). Rather than the F1 Academy-style workaround of
    relabelling extra sessions to an unrelated SessionType (see ADR-016),
    same-type sessions within one event are merged into a single Session
    spanning from the first slot's start to the last slot's end — an
    honest simplification (a calendar entry "Qualifying, 15:05-16:45" is
    more useful than four near-duplicate 25-minute entries), and it keeps
    UID uniqueness for free instead of via a relabelling trick.
  - Pre-season test days ("Official Tests - X", "Collective Tests - X")
    are excluded from the season's race list — they are not championship
    rounds, and (per Sprint 35 investigation) their session structure
    doesn't fit the FP/Qualifying/Race shape at all ("Morning Session" /
    "Afternoon Session" repeated across multiple days, which would also
    collide on SessionType). Every other provider in this project already
    only covers championship rounds, not private testing.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import UTC, datetime, timedelta
import json
import re
from typing import Any, cast

from bs4 import BeautifulSoup
import httpx

from motorsport_calendar.cache import HttpCache
from motorsport_calendar.core.datasource import HtmlDataSource
from motorsport_calendar.models import (
    Championship,
    Circuit,
    Event,
    Session,
    SessionType,
)

_TIMEOUT = 10.0

# Slugs containing these substrings are pre-season testing, not championship
# rounds — excluded from every ACO series season list (see module docstring).
# "prologue" added Sprint 48 for WEC's own pre-season test slug
# ("official-prologue-imola-2026") — never present in ELMS/MLMC slugs
# (verified against every 2026 season-page URL), so purely additive.
_EXCLUDED_SLUG_KEYWORDS = ("official-test", "collective-test", "prologue")

# The top-level event's "endDate" usually coincides closely with the race
# session's end (confirmed for ELMS/MLMC regular rounds: exactly matches
# the announced "4 Hours of X" / race distance). It does NOT always,
# though — Road to Le Mans 2026 reported an endDate ~61 hours after the
# race's own start (likely covering the whole 24 Heures du Mans week, not
# just the RTLM race itself). Only trust endDate for the race's end time
# when it falls within this plausible ceiling; otherwise fall back to the
# generic default duration below.
_MAX_PLAUSIBLE_RACE_DURATION = timedelta(hours=26)

# Session label (as it appears before " - {event name}" in the JSON-LD
# subEvent "name") -> (SessionType, default duration in minutes when no
# better signal is available). Order matters: checked top to bottom, first
# match wins. Shared across every ACO series — confirmed identical label
# vocabulary on both europeanlemansseries.com and lemanscup.com.
#
# The three trailing rules (Free Practice 4, Hyperpole, Warm-up) were added
# Sprint 48 for WEC — never present in ELMS/MLMC's JSON-LD (both cap at
# FP1-3/Qualifying/Race), so purely additive: existing ELMS/MLMC parsing is
# unaffected, still tested end-to-end by the real fixtures below.
#   - "Free Practice 4" (Le Mans only, an extra night practice session) maps
#     to the generic FREE_PRACTICE type rather than colliding with FP3 or
#     inventing an unsupported "FP4" SessionType.
#   - "Hyperpole" (WEC's own qualifying-adjacent shootout, distinct
#     SessionType already in the domain model) covers "Hyperpole"/
#     "Hyperpole 1"/"Hyperpole 2" via startswith, same as every other rule.
#   - "Warm-up" (Le Mans race-morning session) maps to TEST — the closest
#     existing SessionType, since the domain model has no dedicated
#     warm-up type; kept distinct from "Free Practice 4" so the two (which
#     coexist on the same Le Mans weekend, ~37h apart) are never merged
#     into one nonsensical multi-day "session".
_LABEL_RULES: list[tuple[str, SessionType, int]] = [
    ("Free Practice 1", SessionType.FP1, 75),
    ("Free Practice 2", SessionType.FP2, 75),
    ("Free Practice 3", SessionType.FP3, 75),
    ("Free Practice 4", SessionType.FREE_PRACTICE, 75),
    ("Bronze Driver Collective Test", SessionType.TEST, 40),
    ("Qualifying", SessionType.QUALIFYING, 25),  # per-class slot length
    ("Hyperpole", SessionType.HYPERPOLE, 20),  # per-class slot length
    ("Warm-up", SessionType.TEST, 45),
    ("Race", SessionType.RACE, 240),  # overridden below via event endDate
]


def _session_type_for_label(label: str) -> tuple[SessionType, int] | None:
    for prefix_or_substr, session_type, default_minutes in _LABEL_RULES:
        if prefix_or_substr == "Qualifying":
            if "Qualifying" in label:
                return session_type, default_minutes
        elif label.startswith(prefix_or_substr):
            return session_type, default_minutes
    return None


class AcoSportsEventSource(HtmlDataSource, ABC):
    """Abstract base for ACO endurance series scraped from their JSON-LD.

    Subclasses declare series-specific configuration; all HTTP, cache, HTML
    parsing, session-type mapping and merging logic is provided here.

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
        """ICS UID prefix and circuit-id prefix, e.g. 'elms', 'mlmc'."""

    @property
    @abstractmethod
    def _base_url(self) -> str:
        """Site root, e.g. 'https://www.europeanlemansseries.com'."""

    @property
    @abstractmethod
    def _event_name_prefix(self) -> str:
        """Leading words to strip from the JSON-LD event name, e.g. 'ELMS'."""

    @property
    @abstractmethod
    def _circuit_data(self) -> dict[str, tuple[str, str]]:
        """JSON-LD ``location.name`` -> (country, IANA timezone)."""

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
        self._client = client or httpx.AsyncClient(
            timeout=_TIMEOUT,
            headers={"User-Agent": "Mozilla/5.0 (compatible; motorsport-calendar)"},
        )
        self._cache = cache if cache is not None else (HttpCache() if client is None else None)
        self._refresh = refresh

    # ------------------------------------------------------------------
    # HtmlDataSource contract
    # ------------------------------------------------------------------

    async def fetch_html(self, url: str) -> str:
        """Fetch raw HTML from *url*; uses cache when available.

        Cache-aware by design (mirrors F1CalendarBaseSource.fetch_json) so
        that patching this single method in tests bypasses HttpCache
        entirely, the same way patching fetch_json does for the JSON-based
        sources — no separate cache-wrapper layer to work around.
        """

        async def _do_fetch(_url: str, _params: dict[str, Any]) -> str:
            response = await self._client.get(_url)
            response.raise_for_status()
            return response.text

        if self._cache is not None:
            # HttpCache is typed for JSON payloads (list | dict) but caches
            # any JSON-serialisable value transparently at runtime — a
            # plain str round-trips through json.dumps/json.loads exactly
            # as given, so reusing it here avoids a second cache
            # implementation for HTML text.
            cached = await self._cache.get_json(url, {}, _do_fetch, refresh=self._refresh)  # type: ignore[arg-type]
            return cast(str, cached)
        return await _do_fetch(url, {})

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get_season(self, year: int) -> list[Event]:
        season_url = f"{self._base_url}/en/season/{year}"
        season_html = await self.fetch_html(season_url)
        race_urls = self._extract_race_urls(season_html, year)

        championship = self._make_championship(year)
        events: list[Event] = []
        for round_number, race_url in enumerate(race_urls, start=1):
            race_html = await self.fetch_html(race_url)
            data = self._extract_json_ld(race_html)
            events.append(self._build_event(championship, data, round_number, year))
        return events

    # ------------------------------------------------------------------
    # Internals — season page scraping
    # ------------------------------------------------------------------

    def _extract_race_urls(self, html: str, year: int) -> list[str]:
        soup = BeautifulSoup(html, "lxml")
        seen: dict[str, None] = {}
        for a in soup.find_all("a", href=True):
            href = str(a["href"]).strip()
            if "/en/race/" not in href:
                continue
            slug = href.rstrip("/").rsplit("/en/race/", 1)[-1]
            if any(kw in slug.lower() for kw in _EXCLUDED_SLUG_KEYWORDS):
                continue
            url = href if href.startswith("http") else f"{self._base_url}{href}"
            if not self._race_url_belongs_to_season(url, year):
                continue
            seen[url] = None
        return list(seen)

    def _race_url_belongs_to_season(self, url: str, year: int) -> bool:
        """Whether *url* (already slug-filtered) belongs to *year*'s season.

        ``True`` unconditionally by default — ELMS/MLMC's season page only
        ever lists the current season, never mixing years. Overridden by
        ``OfficialWecSource`` (Sprint 48), whose ``/en/season/{year}`` page
        embeds *next* year's races too (confirmed empirically: fetching
        ``season/2026`` returns both ``-2026`` and ``-2027`` suffixed race
        slugs in the same page), distinguishable only by that URL suffix.
        """
        return True

    def _extract_json_ld(self, html: str) -> dict[str, Any]:
        soup = BeautifulSoup(html, "lxml")
        tag = soup.find("script", attrs={"type": "application/ld+json"})
        if tag is None or not tag.string:
            return {}
        try:
            parsed: dict[str, Any] = json.loads(tag.string)
        except json.JSONDecodeError:
            return {}
        return parsed

    # ------------------------------------------------------------------
    # Internals — event/session construction
    # ------------------------------------------------------------------

    def _build_event(
        self, championship: Championship, data: dict[str, Any], round_number: int, year: int
    ) -> Event:
        circuit = self._build_circuit(data)
        sessions = self._build_sessions(data)
        raw_name = data.get("name", "")
        name = raw_name.removeprefix(f"{self._event_name_prefix} ").removesuffix(f" {year}")
        return Event(
            championship=championship,
            season=year,
            round=round_number,
            name=name or raw_name,
            circuit=circuit,
            sessions=tuple(sessions),
            event_uid=f"{self._series_key}-{year}-{round_number}@motorsport-calendar",
        )

    def _build_circuit(self, data: dict[str, Any]) -> Circuit:
        location = data.get("location") or {}
        location_name: str = location.get("name", "Unknown")
        country, timezone = self._circuit_data.get(location_name, ("Unknown", "UTC"))
        circuit_id = re.sub(r"[^a-z0-9]+", "-", location_name.lower()).strip("-") or "unknown"
        return Circuit(
            id=f"{self._series_key}-{circuit_id}",
            name=location_name,
            city=location_name,
            country=country,
            timezone=timezone,
        )

    def _race_session_end(
        self, first_start: datetime, event_end: datetime | None, event_name: str
    ) -> datetime | None:
        """The Race session's end time, or ``None`` to fall back to the
        generic default-duration logic below (same as any other session
        type).

        Default implementation: trust the JSON-LD event-level ``endDate``
        when it falls within a plausible ceiling of the race's own start
        (confirmed accurate for ELMS/MLMC regular rounds — see module
        docstring). *event_name* is unused here; it exists so a subclass
        whose ``endDate`` is not a reliable signal at all (see
        ``OfficialWecSource``, Sprint 48) can override this method with a
        name-based duration instead, without needing to reimplement
        ``_build_sessions``.
        """
        if event_end is None:
            return None
        plausible = first_start < event_end <= first_start + _MAX_PLAUSIBLE_RACE_DURATION
        return event_end if plausible else None

    def _build_sessions(self, data: dict[str, Any]) -> list[Session]:
        sub_events: list[dict[str, Any]] = data.get("subEvent") or []
        event_end = self._parse_datetime(data.get("endDate"))
        event_name: str = data.get("name", "")

        groups: dict[SessionType, list[tuple[str, datetime]]] = {}
        for sub in sub_events:
            raw_name: str = sub.get("name", "")
            label = raw_name.split(" - ", 1)[0].strip()
            start = self._parse_datetime(sub.get("startDate"))
            if start is None:
                continue
            match = _session_type_for_label(label)
            if match is None:
                continue
            session_type, _ = match
            groups.setdefault(session_type, []).append((label, start))

        sessions: list[Session] = []
        for session_type, entries in groups.items():
            entries.sort(key=lambda e: e[1])
            first_label, first_start = entries[0]
            _, _, default_minutes = next(
                (r for r in _LABEL_RULES if r[1] == session_type), (None, None, 60)
            )
            race_end = (
                self._race_session_end(first_start, event_end, event_name)
                if session_type is SessionType.RACE
                else None
            )
            end: datetime
            if race_end is not None:
                end = race_end
            elif len(entries) > 1:
                _, last_start = entries[-1]
                end = last_start + timedelta(minutes=default_minutes)
            else:
                end = first_start + timedelta(minutes=default_minutes)
            title = (
                session_type.value.replace("_", " ").title() if len(entries) > 1 else first_label
            )
            sessions.append(
                Session(
                    type=session_type, start_datetime=first_start, end_datetime=end, title=title
                )
            )

        sessions.sort(key=lambda s: s.start_datetime)
        return sessions

    @staticmethod
    def _parse_datetime(value: str | None) -> datetime | None:
        """Parse an ISO 8601 timestamp and normalise it to UTC.

        The JSON-LD reports each timestamp with the circuit's local fixed
        UTC offset (e.g. ``+02:00``), not UTC itself and not an IANA zone
        name. Left as-is, ``fromisoformat`` returns a bare
        ``datetime.timezone(timedelta(hours=2))`` with no IANA identity;
        ``IcsExporter`` would then hand it to ``icalendar``, which emits a
        synthetic, non-standard ``TZID="UTC+02:00"`` with no accompanying
        ``VTIMEZONE`` block (invalid per RFC 5545 — some calendar clients
        silently misread the offset, others reject the event outright).
        Normalising here instead keeps every session in this project's
        established UTC-everywhere convention (see
        ``PulseliveBase._parse_datetime`` and ``SroTimetableBase``), so
        ``IcsExporter`` always emits a plain ``Z``-suffixed ``DTSTART``
        that needs no ``VTIMEZONE`` at all — bug found and fixed in MC-002
        (P0-1), MC-001 §5.
        """
        if not value:
            return None
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            return None
        return parsed.astimezone(UTC)
