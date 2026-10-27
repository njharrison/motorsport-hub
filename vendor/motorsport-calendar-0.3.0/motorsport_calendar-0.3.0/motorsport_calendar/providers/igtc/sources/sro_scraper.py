"""SroScraperSource — IGTC source scraped from intercontinentalgtchallenge.com.

Delegates all HTTP, cache, HTML-table parsing and session-mapping logic to
SroTimetableSource. Only IGTC-specific configuration (base URL,
championship) lives here — the circuit table is shared with GT World
Challenge Europe/America/Asia (confirmed same CMS/URL scheme, see
``sro_series/timetable_base.py`` module docstring for the full
investigation).

Source: https://www.intercontinentalgtchallenge.com (``/calendar`` for the
round list, ``/event/{id}/{slug}`` per-round HTML timetable tables). Two of
IGTC's five rounds (CrowdStrike 24 Hours of Spa, Indianapolis 8 Hour) are
also separately calendared by GT World Challenge Europe/America under
their own event IDs — this is expected and not deduplicated: IGTC awards
its own championship points at these rounds independently of the regional
series, so it is presented here as its own full-fledged championship, the
same as every other provider in this project (no cross-championship
deduplication exists anywhere in this codebase).
"""

from __future__ import annotations

from motorsport_calendar.models import Championship, ChampionshipCategory
from motorsport_calendar.providers.igtc.source import IgtcSource
from motorsport_calendar.providers.sro_series.timetable_base import SroTimetableSource

__all__ = ["SroScraperSource"]


class SroScraperSource(SroTimetableSource, IgtcSource):
    """IGTC source backed by intercontinentalgtchallenge.com's HTML.

    Inherits all HTTP, cache, HTML-parsing and session-mapping logic from
    SroTimetableSource. The two members below are the only IGTC-specific
    configuration.
    """

    @property
    def _series_key(self) -> str:
        return "igtc"

    @property
    def _base_url(self) -> str:
        return "https://www.intercontinentalgtchallenge.com"

    def _make_championship(self, year: int) -> Championship:
        return Championship(
            id=f"igtc-{year}",
            name="Intercontinental GT Challenge",
            category=ChampionshipCategory.GT,
        )
