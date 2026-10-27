"""SroScraperSource — GT World Challenge America source scraped from gt-world-challenge-america.com.

Delegates all HTTP, cache, HTML-table parsing and session-mapping logic to
SroTimetableSource. Only GT World Challenge America-specific configuration
(base URL, championship) lives here — the circuit table is shared with
GT World Challenge Europe/Asia and IGTC (confirmed same CMS/URL scheme,
see ``sro_series/timetable_base.py`` module docstring for the full
investigation).

Source: https://www.gt-world-challenge-america.com (``/calendar`` for the
round list, ``/event/{id}/{slug}`` per-round HTML timetable tables).
"""

from __future__ import annotations

from motorsport_calendar.models import Championship, ChampionshipCategory
from motorsport_calendar.providers.gtwc_america.source import GtwcAmericaSource
from motorsport_calendar.providers.sro_series.timetable_base import SroTimetableSource

__all__ = ["SroScraperSource"]


class SroScraperSource(SroTimetableSource, GtwcAmericaSource):
    """GT World Challenge America source backed by gt-world-challenge-america.com's HTML.

    Inherits all HTTP, cache, HTML-parsing and session-mapping logic from
    SroTimetableSource. The two members below are the only
    GT World Challenge America-specific configuration.
    """

    @property
    def _series_key(self) -> str:
        return "gtwc-america"

    @property
    def _base_url(self) -> str:
        return "https://www.gt-world-challenge-america.com"

    def _make_championship(self, year: int) -> Championship:
        return Championship(
            id=f"gtwc-america-{year}",
            name="GT World Challenge America Powered by AWS",
            category=ChampionshipCategory.GT,
        )
