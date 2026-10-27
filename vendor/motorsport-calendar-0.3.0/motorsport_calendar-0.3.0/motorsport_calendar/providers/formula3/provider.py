"""Formula3Provider — F3 implementation of the Provider ABC."""

from motorsport_calendar.models import Championship, ChampionshipCategory, Event
from motorsport_calendar.providers.base import Provider
from motorsport_calendar.providers.formula3.source import Formula3Source


class Formula3Provider(Provider):
    """Provides FIA Formula 3 calendar data via a pluggable Formula3Source.

    The source is injected at construction time; the provider contains no
    download or parsing logic — it only delegates to the source and maps
    the result to the shared domain models.

    Usage::

        provider = Formula3Provider(F1CalendarSource())
        events = await provider.fetch_events("formula3", 2025)
    """

    def __init__(self, source: Formula3Source) -> None:
        self._source = source

    @property
    def name(self) -> str:
        return "formula3"

    @property
    def supported_championships(self) -> list[str]:
        return ["formula3"]

    async def fetch_championship(self, championship_id: str, year: int) -> Championship:
        return Championship(
            id=f"formula3-{year}",
            name="FIA Formula 3 Championship",
            category=ChampionshipCategory.SINGLE_SEATER,
        )

    async def fetch_events(self, championship_id: str, year: int) -> list[Event]:
        return await self._source.get_season(year)
