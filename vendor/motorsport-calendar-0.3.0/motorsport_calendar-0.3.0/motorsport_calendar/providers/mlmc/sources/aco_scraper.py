"""AcoScraperSource — MLMC source scraped from lemanscup.com.

Delegates all HTTP, cache, HTML/JSON-LD parsing and session-merging logic
to AcoSportsEventSource. Only MLMC-specific configuration (base URL, event
name prefix, championship) lives here — the circuit table is shared with
ELMS (confirmed co-located venues, see ``aco_series/circuit_data.py``).

Source: https://www.lemanscup.com (season list + per-race schema.org
JSON-LD — see ``aco_series/sports_event_base.py`` module docstring for the
full investigation). Road to Le Mans appears as just another round on the
same season page — no special handling needed, it flows through the exact
same scraping pipeline as every other round.

Coverage: current season only — same limitation as ELMS (no season
archive by year on the site, verified Sprint 35).
"""

from __future__ import annotations

from motorsport_calendar.models import Championship, ChampionshipCategory
from motorsport_calendar.providers.aco_series.circuit_data import ACO_CIRCUIT_DATA
from motorsport_calendar.providers.aco_series.sports_event_base import AcoSportsEventSource
from motorsport_calendar.providers.mlmc.source import MlmcSource

__all__ = ["AcoScraperSource"]


class AcoScraperSource(AcoSportsEventSource, MlmcSource):
    """MLMC source backed by lemanscup.com's JSON-LD.

    Inherits all HTTP, cache, HTML-parsing and session-merging logic from
    AcoSportsEventSource. The four properties below are the only
    MLMC-specific configuration.
    """

    @property
    def _series_key(self) -> str:
        return "mlmc"

    @property
    def _base_url(self) -> str:
        return "https://www.lemanscup.com"

    @property
    def _event_name_prefix(self) -> str:
        return "Michelin Le Mans Cup"

    @property
    def _circuit_data(self) -> dict[str, tuple[str, str]]:
        return ACO_CIRCUIT_DATA

    def _make_championship(self, year: int) -> Championship:
        return Championship(
            id=f"mlmc-{year}",
            name="Michelin Le Mans Cup",
            category=ChampionshipCategory.ENDURANCE,
        )
