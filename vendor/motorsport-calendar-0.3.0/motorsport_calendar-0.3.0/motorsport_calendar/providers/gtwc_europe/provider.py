"""GtwcEuropeProvider — GT World Challenge Europe implementation of the Provider ABC."""

from motorsport_calendar.models import Championship, ChampionshipCategory, Event
from motorsport_calendar.providers.base import Provider
from motorsport_calendar.providers.gtwc_europe.source import GtwcEuropeSource


class GtwcEuropeProvider(Provider):
    """Provides GT World Challenge Europe calendar data via a pluggable source.

    The source is injected at construction time; the provider contains no
    download or parsing logic — it only delegates to the source and maps
    the result to the shared domain models.

    Usage::

        provider = GtwcEuropeProvider(SroScraperSource())
        events = await provider.fetch_events("gtwc-europe", 2026)
    """

    def __init__(self, source: GtwcEuropeSource) -> None:
        self._source = source

    @property
    def name(self) -> str:
        return "gtwc-europe"

    @property
    def supported_championships(self) -> list[str]:
        return ["gtwc-europe"]

    async def fetch_championship(self, championship_id: str, year: int) -> Championship:
        return Championship(
            id=f"gtwc-europe-{year}",
            name="GT World Challenge Europe Powered by AWS",
            category=ChampionshipCategory.GT,
        )

    async def fetch_events(self, championship_id: str, year: int) -> list[Event]:
        return await self._source.get_season(year)
