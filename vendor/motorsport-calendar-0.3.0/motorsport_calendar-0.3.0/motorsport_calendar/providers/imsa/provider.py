"""ImsaProvider — IMSA WeatherTech SportsCar Championship implementation of Provider."""

from motorsport_calendar.models import Championship, ChampionshipCategory, Event
from motorsport_calendar.providers.base import Provider
from motorsport_calendar.providers.imsa.source import ImsaSource


class ImsaProvider(Provider):
    """Provides IMSA calendar data via a pluggable ImsaSource.

    The source is injected at construction time; the provider contains no
    download or parsing logic — it only delegates to the source and maps
    the result to the shared domain models.

    Usage::

        provider = ImsaProvider(OfficialImsaSource())
        events = await provider.fetch_events("imsa", 2026)
    """

    def __init__(self, source: ImsaSource) -> None:
        self._source = source

    # ------------------------------------------------------------------
    # Provider identity
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        return "imsa"

    @property
    def supported_championships(self) -> list[str]:
        return ["imsa"]

    # ------------------------------------------------------------------
    # Provider contract
    # ------------------------------------------------------------------

    async def fetch_championship(self, championship_id: str, year: int) -> Championship:
        """Return the IMSA Championship descriptor for the given year."""
        return Championship(
            id=f"imsa-{year}",
            name="IMSA WeatherTech SportsCar Championship",
            category=ChampionshipCategory.ENDURANCE,
        )

    async def fetch_events(self, championship_id: str, year: int) -> list[Event]:
        """Delegate season fetching entirely to the injected source."""
        return await self._source.get_season(year)
