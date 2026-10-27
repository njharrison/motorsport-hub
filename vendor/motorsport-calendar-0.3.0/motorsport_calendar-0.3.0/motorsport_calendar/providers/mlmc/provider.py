"""MlmcProvider — Michelin Le Mans Cup implementation of the Provider ABC."""

from motorsport_calendar.models import Championship, ChampionshipCategory, Event
from motorsport_calendar.providers.base import Provider
from motorsport_calendar.providers.mlmc.source import MlmcSource


class MlmcProvider(Provider):
    """Provides Michelin Le Mans Cup calendar data via a pluggable MlmcSource.

    The source is injected at construction time; the provider contains no
    download or parsing logic — it only delegates to the source and maps
    the result to the shared domain models.

    Usage::

        provider = MlmcProvider(AcoScraperSource())
        events = await provider.fetch_events("mlmc", 2026)
    """

    def __init__(self, source: MlmcSource) -> None:
        self._source = source

    @property
    def name(self) -> str:
        return "mlmc"

    @property
    def supported_championships(self) -> list[str]:
        return ["mlmc"]

    async def fetch_championship(self, championship_id: str, year: int) -> Championship:
        return Championship(
            id=f"mlmc-{year}",
            name="Michelin Le Mans Cup",
            category=ChampionshipCategory.ENDURANCE,
        )

    async def fetch_events(self, championship_id: str, year: int) -> list[Event]:
        return await self._source.get_season(year)
