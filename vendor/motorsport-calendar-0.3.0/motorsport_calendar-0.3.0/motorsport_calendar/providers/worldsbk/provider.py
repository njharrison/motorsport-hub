"""WorldSbkProvider — World Superbike (WorldSBK) implementation of Provider."""

from motorsport_calendar.models import Championship, ChampionshipCategory, Event
from motorsport_calendar.providers.base import Provider
from motorsport_calendar.providers.worldsbk.source import WorldSbkSource


class WorldSbkProvider(Provider):
    """Provides WorldSBK calendar data via a pluggable WorldSbkSource.

    The source is injected at construction time; the provider contains no
    download or parsing logic — it only delegates to the source and maps
    the result to the shared domain models.

    Usage::

        provider = WorldSbkProvider(OfficialWorldSbkSource())
        events = await provider.fetch_events("worldsbk", 2026)
    """

    def __init__(self, source: WorldSbkSource) -> None:
        self._source = source

    @property
    def name(self) -> str:
        return "worldsbk"

    @property
    def supported_championships(self) -> list[str]:
        return ["worldsbk"]

    async def fetch_championship(self, championship_id: str, year: int) -> Championship:
        return Championship(
            id=f"worldsbk-{year}",
            name="FIM Superbike World Championship",
            category=ChampionshipCategory.MOTORBIKE,
        )

    async def fetch_events(self, championship_id: str, year: int) -> list[Event]:
        return await self._source.get_season(year)
