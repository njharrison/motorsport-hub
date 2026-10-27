"""SroScraperSource — GT World Challenge Asia source scraped from gt-world-challenge-asia.com.

Delegates all HTTP, cache, HTML-table parsing and session-mapping logic to
SroTimetableSource. Only GT World Challenge Asia-specific configuration
(base URL, championship) lives here — the circuit table is shared with
GT World Challenge Europe/America and IGTC (confirmed same CMS/URL scheme,
see ``sro_series/timetable_base.py`` module docstring for the full
investigation).

Source: https://www.gt-world-challenge-asia.com (``/calendar`` for the
round list, ``/event/{id}/{slug}`` per-round HTML timetable tables). Note:
the site labels some rounds "Round N & M" (one venue hosting a
double-header weekend) — this provider ignores that text and re-numbers
rounds sequentially itself, like every other provider in this project (see
``SroTimetableSource.get_season``), rather than trying to reproduce the
site's own compound numbering.
"""

from __future__ import annotations

from motorsport_calendar.models import Championship, ChampionshipCategory
from motorsport_calendar.providers.gtwc_asia.source import GtwcAsiaSource
from motorsport_calendar.providers.sro_series.timetable_base import SroTimetableSource

__all__ = ["SroScraperSource"]


class SroScraperSource(SroTimetableSource, GtwcAsiaSource):
    """GT World Challenge Asia source backed by gt-world-challenge-asia.com's HTML.

    Inherits all HTTP, cache, HTML-parsing and session-mapping logic from
    SroTimetableSource. The two members below are the only
    GT World Challenge Asia-specific configuration.
    """

    @property
    def _series_key(self) -> str:
        return "gtwc-asia"

    @property
    def _base_url(self) -> str:
        return "https://www.gt-world-challenge-asia.com"

    def _make_championship(self, year: int) -> Championship:
        return Championship(
            id=f"gtwc-asia-{year}",
            name="GT World Challenge Asia Powered by AWS",
            category=ChampionshipCategory.GT,
        )
