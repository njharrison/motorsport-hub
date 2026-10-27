"""AcoScraperSource — ELMS source scraped from europeanlemansseries.com.

Delegates all HTTP, cache, HTML/JSON-LD parsing and session-merging logic
to AcoSportsEventSource. Only ELMS-specific configuration (base URL, event
name prefix, championship) lives here — the circuit table is shared with
Michelin Le Mans Cup (confirmed co-located venues, see
``aco_series/circuit_data.py``).

Source: https://www.europeanlemansseries.com (season list + per-race
schema.org JSON-LD — see ``aco_series/sports_event_base.py`` module
docstring for the full investigation).

Coverage: current season only — the site does not expose a season archive
by year (``/en/season/{year}`` 404s for any year other than the current
one, verified Sprint 35). ``get_season()`` for an unavailable year
propagates the underlying ``httpx.HTTPStatusError``, consistent with every
other source in this project.
"""

from __future__ import annotations

from motorsport_calendar.models import Championship, ChampionshipCategory
from motorsport_calendar.providers.aco_series.circuit_data import ACO_CIRCUIT_DATA
from motorsport_calendar.providers.aco_series.sports_event_base import AcoSportsEventSource
from motorsport_calendar.providers.elms.source import ElmsSource

__all__ = ["AcoScraperSource"]


class AcoScraperSource(AcoSportsEventSource, ElmsSource):
    """ELMS source backed by europeanlemansseries.com's JSON-LD.

    Inherits all HTTP, cache, HTML-parsing and session-merging logic from
    AcoSportsEventSource. The four properties below are the only
    ELMS-specific configuration.
    """

    @property
    def _series_key(self) -> str:
        return "elms"

    @property
    def _base_url(self) -> str:
        return "https://www.europeanlemansseries.com"

    @property
    def _event_name_prefix(self) -> str:
        return "ELMS"

    @property
    def _circuit_data(self) -> dict[str, tuple[str, str]]:
        return ACO_CIRCUIT_DATA

    def _make_championship(self, year: int) -> Championship:
        return Championship(
            id=f"elms-{year}",
            name="European Le Mans Series",
            category=ChampionshipCategory.ENDURANCE,
        )
