"""IgtcProvider — Intercontinental GT Challenge implementation of the Provider ABC."""

from motorsport_calendar.models import Championship, ChampionshipCategory, Event
from motorsport_calendar.providers.base import Provider
from motorsport_calendar.providers.igtc.source import IgtcSource


class IgtcProvider(Provider):
    """Provides Intercontinental GT Challenge calendar data via a pluggable source.

    The source is injected at construction time; the provider contains no
    download or parsing logic — it only delegates to the source and maps
    the result to the shared domain models.

    Usage::

        provider = IgtcProvider(SroScraperSource())
        events = await provider.fetch_events("igtc", 2026)
    """

    def __init__(self, source: IgtcSource) -> None:
        self._source = source

    @property
    def name(self) -> str:
        return "igtc"

    @property
    def supported_championships(self) -> list[str]:
        return ["igtc"]

    async def fetch_championship(self, championship_id: str, year: int) -> Championship:
        return Championship(
            id=f"igtc-{year}",
            name="Intercontinental GT Challenge",
            category=ChampionshipCategory.GT,
        )

    async def fetch_events(self, championship_id: str, year: int) -> list[Event]:
        return await self._source.get_season(year)
