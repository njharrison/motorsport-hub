"""Moto2Provider — Moto2 implementation of the Provider ABC."""

from motorsport_calendar.models import Championship, ChampionshipCategory, Event
from motorsport_calendar.providers.base import Provider
from motorsport_calendar.providers.moto2.source import Moto2Source


class Moto2Provider(Provider):
    """Provides Moto2 calendar data via a pluggable source.

    The source is injected at construction time; the provider contains no
    download or parsing logic — it only delegates to the source and maps
    the result to the shared domain models.

    Usage::

        provider = Moto2Provider(PulseliveSource())
        events = await provider.fetch_events("moto2", 2026)
    """

    def __init__(self, source: Moto2Source) -> None:
        self._source = source

    @property
    def name(self) -> str:
        return "moto2"

    @property
    def supported_championships(self) -> list[str]:
        return ["moto2"]

    async def fetch_championship(self, championship_id: str, year: int) -> Championship:
        return Championship(
            id=f"moto2-{year}",
            name="Moto2",
            category=ChampionshipCategory.MOTORBIKE,
        )

    async def fetch_events(self, championship_id: str, year: int) -> list[Event]:
        return await self._source.get_season(year)
