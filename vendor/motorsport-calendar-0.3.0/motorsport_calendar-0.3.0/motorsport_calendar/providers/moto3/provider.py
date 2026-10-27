"""Moto3Provider — Moto3 implementation of the Provider ABC."""

from motorsport_calendar.models import Championship, ChampionshipCategory, Event
from motorsport_calendar.providers.base import Provider
from motorsport_calendar.providers.moto3.source import Moto3Source


class Moto3Provider(Provider):
    """Provides Moto3 calendar data via a pluggable source.

    The source is injected at construction time; the provider contains no
    download or parsing logic — it only delegates to the source and maps
    the result to the shared domain models.

    Usage::

        provider = Moto3Provider(PulseliveSource())
        events = await provider.fetch_events("moto3", 2026)
    """

    def __init__(self, source: Moto3Source) -> None:
        self._source = source

    @property
    def name(self) -> str:
        return "moto3"

    @property
    def supported_championships(self) -> list[str]:
        return ["moto3"]

    async def fetch_championship(self, championship_id: str, year: int) -> Championship:
        return Championship(
            id=f"moto3-{year}",
            name="Moto3",
            category=ChampionshipCategory.MOTORBIKE,
        )

    async def fetch_events(self, championship_id: str, year: int) -> list[Event]:
        return await self._source.get_season(year)
