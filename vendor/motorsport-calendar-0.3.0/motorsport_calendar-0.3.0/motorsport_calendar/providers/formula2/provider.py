"""Formula2Provider — F2 implementation of the Provider ABC."""

from motorsport_calendar.models import Championship, ChampionshipCategory, Event
from motorsport_calendar.providers.base import Provider
from motorsport_calendar.providers.formula2.source import Formula2Source


class Formula2Provider(Provider):
    """Provides Formula 2 calendar data via a pluggable Formula2Source.

    The source is injected at construction time; the provider contains no
    download or parsing logic — it only delegates to the source and maps
    the result to the shared domain models.

    Usage::

        provider = Formula2Provider(F1CalendarSource())
        events = await provider.fetch_events("formula2", 2025)
    """

    def __init__(self, source: Formula2Source) -> None:
        self._source = source

    @property
    def name(self) -> str:
        return "formula2"

    @property
    def supported_championships(self) -> list[str]:
        return ["formula2"]

    async def fetch_championship(self, championship_id: str, year: int) -> Championship:
        return Championship(
            id=f"formula2-{year}",
            name="FIA Formula 2 Championship",
            category=ChampionshipCategory.SINGLE_SEATER,
        )

    async def fetch_events(self, championship_id: str, year: int) -> list[Event]:
        return await self._source.get_season(year)
