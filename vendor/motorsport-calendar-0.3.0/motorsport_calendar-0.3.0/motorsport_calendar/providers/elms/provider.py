"""ElmsProvider — European Le Mans Series implementation of the Provider ABC."""

from motorsport_calendar.models import Championship, ChampionshipCategory, Event
from motorsport_calendar.providers.base import Provider
from motorsport_calendar.providers.elms.source import ElmsSource


class ElmsProvider(Provider):
    """Provides ELMS calendar data via a pluggable ElmsSource.

    The source is injected at construction time; the provider contains no
    download or parsing logic — it only delegates to the source and maps
    the result to the shared domain models.

    Usage::

        provider = ElmsProvider(AcoScraperSource())
        events = await provider.fetch_events("elms", 2026)
    """

    def __init__(self, source: ElmsSource) -> None:
        self._source = source

    @property
    def name(self) -> str:
        return "elms"

    @property
    def supported_championships(self) -> list[str]:
        return ["elms"]

    async def fetch_championship(self, championship_id: str, year: int) -> Championship:
        return Championship(
            id=f"elms-{year}",
            name="European Le Mans Series",
            category=ChampionshipCategory.ENDURANCE,
        )

    async def fetch_events(self, championship_id: str, year: int) -> list[Event]:
        return await self._source.get_season(year)
