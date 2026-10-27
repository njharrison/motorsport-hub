"""Formula1Provider — F1 implementation of the Provider ABC."""

from motorsport_calendar.models import Championship, ChampionshipCategory, Event
from motorsport_calendar.providers.base import Provider
from motorsport_calendar.providers.formula1.source import Formula1Source


class Formula1Provider(Provider):
    """Provides Formula 1 calendar data via a pluggable Formula1Source.

    The source is injected at construction time; the provider contains no
    download or parsing logic — it only delegates to the source and maps
    the result to the shared domain models.

    Usage::

        provider = Formula1Provider(OpenF1Source())
        events = await provider.fetch_events("formula1", 2025)
    """

    def __init__(self, source: Formula1Source) -> None:
        self._source = source

    # ------------------------------------------------------------------
    # Provider identity
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        return "formula1"

    @property
    def supported_championships(self) -> list[str]:
        return ["formula1"]

    # ------------------------------------------------------------------
    # Provider contract
    # ------------------------------------------------------------------

    async def fetch_championship(self, championship_id: str, year: int) -> Championship:
        """Return the F1 Championship descriptor for the given year."""
        return Championship(
            id=f"formula1-{year}",
            name="Formula 1 World Championship",
            category=ChampionshipCategory.SINGLE_SEATER,
        )

    async def fetch_events(self, championship_id: str, year: int) -> list[Event]:
        """Delegate season fetching entirely to the injected source."""
        return await self._source.get_season(year)
