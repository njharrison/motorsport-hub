"""F1AcademyProvider — F1 Academy implementation of the Provider ABC."""

from motorsport_calendar.models import Championship, ChampionshipCategory, Event
from motorsport_calendar.providers.base import Provider
from motorsport_calendar.providers.f1_academy.source import F1AcademySource


class F1AcademyProvider(Provider):
    """Provides F1 Academy calendar data via a pluggable F1AcademySource.

    The source is injected at construction time; the provider contains no
    download or parsing logic — it only delegates to the source and maps
    the result to the shared domain models.

    Usage::

        provider = F1AcademyProvider(F1CalendarSource())
        events = await provider.fetch_events("f1-academy", 2025)
    """

    def __init__(self, source: F1AcademySource) -> None:
        self._source = source

    @property
    def name(self) -> str:
        return "f1-academy"

    @property
    def supported_championships(self) -> list[str]:
        return ["f1-academy"]

    async def fetch_championship(self, championship_id: str, year: int) -> Championship:
        return Championship(
            id=f"f1-academy-{year}",
            name="F1 Academy",
            category=ChampionshipCategory.SINGLE_SEATER,
        )

    async def fetch_events(self, championship_id: str, year: int) -> list[Event]:
        return await self._source.get_season(year)
