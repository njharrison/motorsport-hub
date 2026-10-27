"""Abstract base for SRO-organised GT series scraped via HTML timetable tables.

GT World Challenge Europe, GT World Challenge America, GT World Challenge Asia
and the Intercontinental GT Challenge (IGTC) are all organised by SRO
Motorsports Group and run on the same web platform — confirmed empirically
(Sprint 37) across all four ``.com`` sites: identical ``/event/{id}/{slug}``
URL scheme, identical calendar-page structure (each championship round has a
"Round N" label next to its link; pre-season test days and other
non-championship entries have none), and identical per-event page structure
(one ``<table class="timetable__table">`` per calendar day, three columns:
Session / Local Time / GMT).

Unlike the ACO series (Sprint 35), no JSON-LD is present — no documented or
semi-structured feed exists at all for any of the four sites (confirmed by
inspecting raw HTML, not assumed) — so this is scraping in the literal
"last resort" sense the sprint brief calls for. Session times are read
straight out of the rendered HTML tables. The GMT column gives an exact
UTC time directly, so no per-circuit timezone lookup is needed to compute
session start/end (``Circuit.timezone`` is populated from a maintained
table purely for display — see ``circuit_data.py``).

Real-world quirks handled generically here, not per-series (each confirmed
by fetching real event pages, not assumed):

  - Every session row only gives a *start* time, never an end time — unlike
    ACO's JSON-LD. Duration is inferred: a fixed default per SessionType,
    except RACE/SPRINT, whose duration is inferred from a "N Hour(s)"
    pattern in the event's URL slug when present (e.g. ``bathurst-12-hour``,
    ``crowdstrike-24-hours-of-spa``) — falls back to a generic default
    otherwise (e.g. undocumented distance-based formats such as
    ``suzuka-1000km``, or ordinary sprint-length races).
  - GT World Challenge Europe/Asia run some rounds as a "Sprint Cup"
    double-header (two Qualifying blocks, two Race blocks) and others as a
    single race (Endurance Cup rounds, or GT World Challenge America's
    format, which never doubles up). Rather than assume a fixed session
    count, every event's own Race-labelled entries are counted first:
    exactly one Race -> normal QUALIFYING/RACE; exactly two -> the first
    chronologically is relabelled SPRINT_QUALIFYING/SPRINT (the same trick
    already used for F1 Sprint weekends), the second stays QUALIFYING/RACE.
    Qualifying-family entries are then bucketed against whichever Race they
    chronologically precede.
  - Some endurance rounds (Bathurst 12 Hour) run up to six numbered Free
    Practice sessions across two days — more than the three FP slots the
    domain model has (FP1/FP2/FP3). The first two (chronologically) map to
    FP1/FP2 normally; everything from the third session onward is merged
    into a single FP3 session (spanning from the third session's start to
    the last one's start) rather than dropped, so no real track time
    silently disappears from the count.
  - Non-competitive entries (pre-event testing, ceremonial parades, pit
    walks, warm-up, "pre-qualifying" green-flag sessions) are excluded
    entirely — consistent with every other provider in this project only
    covering championship-relevant track sessions (see the ACO test-day
    exclusion, Sprint 35).
  - A handful of far-future rounds have an empty timetable (SRO has not
    published the schedule yet, confirmed live for GT World Challenge
    America's Indianapolis 8 Hour 2026) — these are skipped entirely from
    the season's event list rather than emitted with zero sessions.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import UTC, date, datetime, time, timedelta
import re
from typing import Any, cast
from urllib.parse import quote, urlparse

from bs4 import BeautifulSoup, Tag
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

from .circuit_data import SRO_CIRCUIT_DATA

_TIMEOUT = 10.0

# Session labels containing these substrings (case-insensitive) are not
# championship track sessions — excluded before any type classification.
_EXCLUDED_LABEL_KEYWORDS = (
    "test",
    "parade",
    "pit walk",
    "warm-up",
    "warm up",
    "pre-qualifying",
    "pre qualifying",
)

_RACE_LABEL_RE = re.compile(r"^(main\s+)?race(\s*\d+)?$", re.IGNORECASE)
_HOUR_SLUG_RE = re.compile(r"(\d+)-?hour", re.IGNORECASE)

_DEFAULT_FP_MINUTES = 60
_DEFAULT_QUALIFYING_MINUTES = 60
_DEFAULT_SUPERPOLE_MINUTES = 20
_DEFAULT_RACE_MINUTES = 90  # ordinary sprint/feature race, no "N Hour" slug match
_DEFAULT_SPRINT_MINUTES = 60

_MONTHS = {
    name: i
    for i, name in enumerate(
        (
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December",
        ),
        start=1,
    )
}


def _parse_time_of_day(text: str) -> time | None:
    """Parse "11:00" or "02:35 pm" -> time. Returns None on anything else."""
    text = text.strip()
    for fmt in ("%H:%M", "%I:%M %p"):
        try:
            return datetime.strptime(text, fmt).time()
        except ValueError:
            continue
    return None


def _classify_label(label: str) -> str | None:
    """Return "race" / "qualifying" / "practice" / "superpole", or None to skip."""
    lowered = label.strip().lower()
    if any(kw in lowered for kw in _EXCLUDED_LABEL_KEYWORDS):
        return None
    if _RACE_LABEL_RE.match(label.strip()):
        return "race"
    if "superpole" in lowered:
        return "superpole"
    if "qualifying" in lowered:
        return "qualifying"
    if "practice" in lowered or lowered == "bronze session":
        return "practice"
    return None


class SroTimetableSource(HtmlDataSource, ABC):
    """Abstract base for SRO GT series scraped from their HTML timetables.

    Subclasses declare only series-specific configuration; all HTTP, cache,
    HTML parsing, session-type mapping and duration-inference logic is
    provided here.

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
        """ICS UID prefix and circuit-id prefix, e.g. 'gtwc-europe', 'igtc'."""

    @property
    @abstractmethod
    def _base_url(self) -> str:
        """Site root, e.g. 'https://www.gt-world-challenge-europe.com'."""

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

        Cache-aware by design (mirrors F1CalendarBaseSource.fetch_json and
        AcoSportsEventSource.fetch_html) so that patching this single
        method in tests bypasses HttpCache entirely.
        """

        async def _do_fetch(_url: str, _params: dict[str, Any]) -> str:
            response = await self._client.get(_url)
            response.raise_for_status()
            return response.text

        if self._cache is not None:
            cached = await self._cache.get_json(url, {}, _do_fetch, refresh=self._refresh)  # type: ignore[arg-type]
            return cast(str, cached)
        return await _do_fetch(url, {})

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get_season(self, year: int) -> list[Event]:
        calendar_html = await self.fetch_html(f"{self._base_url}/calendar")
        event_urls = self._extract_round_urls(calendar_html)

        championship = self._make_championship(year)
        events: list[Event] = []
        round_number = 0
        for event_url in event_urls:
            event_html = await self.fetch_html(event_url)
            event = self._build_event(championship, event_html, event_url, year)
            if event is None:
                continue
            round_number += 1
            events.append(event.model_copy(update={"round": round_number}))
        return events

    # ------------------------------------------------------------------
    # Internals — calendar page scraping
    # ------------------------------------------------------------------

    def _extract_round_urls(self, html: str) -> list[str]:
        soup = BeautifulSoup(html, "lxml")
        found: dict[str, int] = {}
        for span in soup.find_all(class_=_is_round_label_class):
            text = span.get_text(strip=True)
            match = re.search(r"Round\s+(\d+)", text)
            if not match:
                continue
            href = _find_event_href(span)
            if href is None:
                continue
            url = href if href.startswith("http") else f"{self._base_url}{href}"
            url = quote(url, safe=":/?&=")
            round_number = int(match.group(1))
            if url not in found or round_number < found[url]:
                found[url] = round_number
        return [url for url, _ in sorted(found.items(), key=lambda item: item[1])]

    # ------------------------------------------------------------------
    # Internals — event page scraping
    # ------------------------------------------------------------------

    def _build_event(
        self, championship: Championship, html: str, event_url: str, year: int
    ) -> Event | None:
        soup = BeautifulSoup(html, "lxml")
        sessions = self._build_sessions(soup, event_url, year)
        if not sessions:
            return None

        slug = urlparse(event_url).path.rstrip("/").rsplit("/", 1)[-1]
        name = self._extract_event_name(soup) or slug
        circuit = self._build_circuit(soup, slug)

        return Event(
            championship=championship,
            season=year,
            round=1,  # placeholder — overwritten by the caller with the final index
            name=name,
            circuit=circuit,
            sessions=tuple(sessions),
            event_uid=f"{self._series_key}-{year}-{slug}@motorsport-calendar",
        )

    @staticmethod
    def _extract_event_name(soup: BeautifulSoup) -> str | None:
        heading = soup.find(class_=lambda c: c and "feature__heading" in c)
        if heading is None:
            return None
        text = heading.get_text(strip=True)
        return text or None

    def _build_circuit(self, soup: BeautifulSoup, slug: str) -> Circuit:
        known = SRO_CIRCUIT_DATA.get(slug)
        name, tz = known if known is not None else (self._extract_event_name(soup) or slug, "UTC")
        country = self._extract_country(soup)
        circuit_id = re.sub(r"[^a-z0-9]+", "-", slug.lower()).strip("-") or "unknown"
        return Circuit(
            id=f"{self._series_key}-{circuit_id}",
            name=name,
            city=name,
            country=country,
            timezone=tz,
        )

    @staticmethod
    def _extract_country(soup: BeautifulSoup) -> str:
        title = soup.find("title")
        if title is None:
            return "Unknown"
        parts = [p.strip() for p in title.get_text().split(",")]
        return parts[1] if len(parts) >= 3 else "Unknown"

    # ------------------------------------------------------------------
    # Internals — timetable parsing
    # ------------------------------------------------------------------

    def _build_sessions(self, soup: BeautifulSoup, event_url: str, year: int) -> list[Session]:
        raw_entries = self._extract_raw_entries(soup, year)

        by_class: dict[str, list[tuple[str, datetime]]] = {
            "race": [],
            "qualifying": [],
            "practice": [],
            "superpole": [],
        }
        for label, start in raw_entries:
            kind = _classify_label(label)
            if kind is not None:
                by_class[kind].append((label, start))

        race_entries = sorted(by_class["race"], key=lambda e: e[1])
        if not race_entries:
            return []

        sessions: list[Session] = []
        race_slots = race_entries[:2]
        race_types = (
            [SessionType.RACE] if len(race_slots) == 1 else [SessionType.SPRINT, SessionType.RACE]
        )
        slug = urlparse(event_url).path.rstrip("/").rsplit("/", 1)[-1]
        race_duration = self._infer_race_duration(slug)
        sprint_duration = timedelta(minutes=_DEFAULT_SPRINT_MINUTES)
        for (label, start), session_type in zip(race_slots, race_types, strict=True):
            duration = race_duration if session_type is SessionType.RACE else sprint_duration
            sessions.append(
                Session(
                    type=session_type,
                    start_datetime=start,
                    end_datetime=start + duration,
                    title=label,
                )
            )

        sessions.extend(self._build_qualifying_sessions(by_class["qualifying"], race_slots))
        sessions.extend(self._build_practice_sessions(by_class["practice"]))
        sessions.extend(self._build_superpole_sessions(by_class["superpole"]))

        sessions.sort(key=lambda s: s.start_datetime)
        return sessions

    @staticmethod
    def _build_qualifying_sessions(
        entries: list[tuple[str, datetime]], race_slots: list[tuple[str, datetime]]
    ) -> list[Session]:
        if not entries:
            return []
        entries = sorted(entries, key=lambda e: e[1])
        buckets: dict[int, list[tuple[str, datetime]]] = {}
        for label, start in entries:
            bucket_index = len(race_slots) - 1
            for i, (_, race_start) in enumerate(race_slots):
                if start < race_start:
                    bucket_index = i
                    break
            buckets.setdefault(bucket_index, []).append((label, start))

        sessions: list[Session] = []
        for bucket_index, bucket_entries in buckets.items():
            session_type = (
                SessionType.SPRINT_QUALIFYING
                if bucket_index == 0 and len(race_slots) == 2
                else SessionType.QUALIFYING
            )
            first_start = bucket_entries[0][1]
            last_start = bucket_entries[-1][1]
            end = last_start + timedelta(minutes=_DEFAULT_QUALIFYING_MINUTES)
            title = bucket_entries[0][0] if len(bucket_entries) == 1 else "Qualifying"
            sessions.append(
                Session(
                    type=session_type,
                    start_datetime=first_start,
                    end_datetime=end,
                    title=title,
                )
            )
        return sessions

    @staticmethod
    def _build_practice_sessions(entries: list[tuple[str, datetime]]) -> list[Session]:
        if not entries:
            return []
        entries = sorted(entries, key=lambda e: e[1])
        sessions: list[Session] = []
        fp_types = [SessionType.FP1, SessionType.FP2, SessionType.FP3]
        for i, session_type in enumerate(fp_types):
            if i >= len(entries):
                break
            if i == 2 and len(entries) > 3:
                overflow = entries[i:]
                label, start = overflow[0]
                end = overflow[-1][1] + timedelta(minutes=_DEFAULT_FP_MINUTES)
            else:
                label, start = entries[i]
                end = start + timedelta(minutes=_DEFAULT_FP_MINUTES)
            sessions.append(
                Session(type=session_type, start_datetime=start, end_datetime=end, title=label)
            )
        return sessions

    @staticmethod
    def _build_superpole_sessions(entries: list[tuple[str, datetime]]) -> list[Session]:
        if not entries:
            return []
        entries = sorted(entries, key=lambda e: e[1])
        first_label, first_start = entries[0]
        last_start = entries[-1][1]
        end = last_start + timedelta(minutes=_DEFAULT_SUPERPOLE_MINUTES)
        title = first_label if len(entries) == 1 else "Superpole"
        return [
            Session(
                type=SessionType.HYPERPOLE,
                start_datetime=first_start,
                end_datetime=end,
                title=title,
            )
        ]

    @staticmethod
    def _infer_race_duration(slug: str) -> timedelta:
        match = _HOUR_SLUG_RE.search(slug)
        if match:
            return timedelta(hours=int(match.group(1)))
        return timedelta(minutes=_DEFAULT_RACE_MINUTES)

    @staticmethod
    def _extract_raw_entries(soup: BeautifulSoup, year: int) -> list[tuple[str, datetime]]:
        entries: list[tuple[str, datetime]] = []
        for container in soup.find_all(class_="timetable__container"):
            caption = container.find(class_="timetable__caption")
            if caption is None:
                continue
            date_ = _parse_caption_date(caption.get_text(strip=True), year)
            if date_ is None:
                continue
            body = container.find(class_="timetable__table-body")
            if body is None:
                continue
            for row in body.find_all("tr"):
                cells = row.find_all("td")
                if len(cells) < 3:
                    continue
                label = cells[0].get_text(strip=True)
                local_text = cells[1].get_text(strip=True)
                gmt_text = cells[2].get_text(strip=True)
                start = _resolve_utc_datetime(date_, local_text, gmt_text)
                if not label or start is None:
                    continue
                entries.append((label, start))
        return entries


def _is_round_label_class(class_value: str | None) -> bool:
    if not class_value:
        return False
    return "race-text" in class_value or "piped-list-span" in class_value


def _find_event_href(span: Tag) -> str | None:
    node: Tag | None = span
    for _ in range(12):
        if node is None:
            return None
        node = node.parent if isinstance(node.parent, Tag) else None
        if node is None:
            return None
        link = node.find("a", href=lambda h: bool(h and "/event/" in h))
        if isinstance(link, Tag):
            href = link.get("href")
            if isinstance(href, str):
                return href
    return None


def _resolve_utc_datetime(local_date: date, local_text: str, gmt_text: str) -> datetime | None:
    """Combine a timetable row's local/GMT time-of-day pair into a UTC instant.

    The day-table caption (e.g. "Friday, 13 February") is the *local*
    calendar day — combining it directly with the GMT column's
    time-of-day is wrong whenever the circuit's UTC offset pushes an
    early-morning local session into the *previous* UTC calendar day
    (confirmed live, Sprint 37: Bathurst 12 Hour's Friday-morning local
    Free Practice 1 is actually Thursday evening UTC). The local/GMT
    time-of-day difference on the same row gives the true offset, so the
    local date anchors the local time-of-day, and that offset converts it
    to UTC — no external timezone database needed.
    """
    local_t = _parse_time_of_day(local_text)
    gmt_t = _parse_time_of_day(gmt_text)
    if local_t is None or gmt_t is None:
        return None
    offset_minutes = (local_t.hour * 60 + local_t.minute) - (gmt_t.hour * 60 + gmt_t.minute)
    if offset_minutes > 720:
        offset_minutes -= 1440
    elif offset_minutes < -720:
        offset_minutes += 1440
    local_dt = datetime.combine(local_date, local_t)
    return (local_dt - timedelta(minutes=offset_minutes)).replace(tzinfo=UTC)


def _parse_caption_date(caption_text: str, year: int) -> date | None:
    match = re.search(r"(\d+)\s+([A-Za-z]+)", caption_text)
    if not match:
        return None
    day = int(match.group(1))
    month = _MONTHS.get(match.group(2).title())
    if month is None:
        return None
    try:
        return date(year, month, day)
    except ValueError:
        return None
