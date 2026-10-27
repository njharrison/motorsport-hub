"""MotoGpProvider — MotoGP implementation of the Provider ABC."""

from motorsport_calendar.models import Championship, ChampionshipCategory, Event
from motorsport_calendar.providers.base import Provider
from motorsport_calendar.providers.motogp.source import MotoGpSource


class MotoGpProvider(Provider):
    """Provides MotoGP calendar data via a pluggable source.

    The source is injected at construction time; the provider contains no
    download or parsing logic — it only delegates to the source and maps
    the result to the shared domain models.

    Usage::

        provider = MotoGpProvider(PulseliveSource())
        events = await provider.fetch_events("motogp", 2026)
    """

    def __init__(self, source: MotoGpSource) -> None:
        self._source = source

    @property
    def name(self) -> str:
        return "motogp"

    @property
    def supported_championships(self) -> list[str]:
        return ["motogp"]

    async def fetch_championship(self, championship_id: str, year: int) -> Championship:
        return Championship(
            id=f"motogp-{year}",
            name="MotoGP",
            category=ChampionshipCategory.MOTORBIKE,
        )

    async def fetch_events(self, championship_id: str, year: int) -> list[Event]:
        return await self._source.get_season(year)
