"""GtwcAsiaProvider — GT World Challenge Asia implementation of the Provider ABC."""

from motorsport_calendar.models import Championship, ChampionshipCategory, Event
from motorsport_calendar.providers.base import Provider
from motorsport_calendar.providers.gtwc_asia.source import GtwcAsiaSource


class GtwcAsiaProvider(Provider):
    """Provides GT World Challenge Asia calendar data via a pluggable source.

    The source is injected at construction time; the provider contains no
    download or parsing logic — it only delegates to the source and maps
    the result to the shared domain models.

    Usage::

        provider = GtwcAsiaProvider(SroScraperSource())
        events = await provider.fetch_events("gtwc-asia", 2026)
    """

    def __init__(self, source: GtwcAsiaSource) -> None:
        self._source = source

    @property
    def name(self) -> str:
        return "gtwc-asia"

    @property
    def supported_championships(self) -> list[str]:
        return ["gtwc-asia"]

    async def fetch_championship(self, championship_id: str, year: int) -> Championship:
        return Championship(
            id=f"gtwc-asia-{year}",
            name="GT World Challenge Asia Powered by AWS",
            category=ChampionshipCategory.GT,
        )

    async def fetch_events(self, championship_id: str, year: int) -> list[Event]:
        return await self._source.get_season(year)
