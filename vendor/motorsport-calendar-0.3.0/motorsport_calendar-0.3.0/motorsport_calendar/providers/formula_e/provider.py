"""FormulaEProvider — Formula E implementation of the Provider ABC."""

from motorsport_calendar.models import Championship, ChampionshipCategory, Event
from motorsport_calendar.providers.base import Provider
from motorsport_calendar.providers.formula_e.source import FormulaESource


class FormulaEProvider(Provider):
    """Provides Formula E calendar data via a pluggable FormulaESource.

    The source is injected at construction time; the provider contains no
    download or parsing logic — it only delegates to the source and maps
    the result to the shared domain models.

    Usage::

        provider = FormulaEProvider(F1CalendarSource())
        events = await provider.fetch_events("formula-e", 2025)
    """

    def __init__(self, source: FormulaESource) -> None:
        self._source = source

    @property
    def name(self) -> str:
        return "formula-e"

    @property
    def supported_championships(self) -> list[str]:
        return ["formula-e"]

    async def fetch_championship(self, championship_id: str, year: int) -> Championship:
        return Championship(
            id=f"formula-e-{year}",
            name="Formula E",
            category=ChampionshipCategory.SINGLE_SEATER,
        )

    async def fetch_events(self, championship_id: str, year: int) -> list[Event]:
        return await self._source.get_season(year)
