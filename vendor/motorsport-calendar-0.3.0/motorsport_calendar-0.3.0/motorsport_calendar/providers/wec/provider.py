"""WecProvider — FIA World Endurance Championship implementation of Provider."""

from motorsport_calendar.models import Championship, ChampionshipCategory, Event
from motorsport_calendar.providers.base import Provider
from motorsport_calendar.providers.wec.source import WecSource


class WecProvider(Provider):
    """Provides FIA WEC calendar data via a pluggable WecSource.

    The source is injected at construction time; the provider contains no
    download or parsing logic — it only delegates to the source and maps
    the result to the shared domain models.

    Usage::

        provider = WecProvider(OfficialWecSource())
        events = await provider.fetch_events("wec", 2026)
    """

    def __init__(self, source: WecSource) -> None:
        self._source = source

    # ------------------------------------------------------------------
    # Provider identity
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        return "wec"

    @property
    def supported_championships(self) -> list[str]:
        return ["wec"]

    # ------------------------------------------------------------------
    # Provider contract
    # ------------------------------------------------------------------

    async def fetch_championship(self, championship_id: str, year: int) -> Championship:
        """Return the WEC Championship descriptor for the given year."""
        return Championship(
            id=f"wec-{year}",
            name="FIA World Endurance Championship",
            category=ChampionshipCategory.ENDURANCE,
        )

    async def fetch_events(self, championship_id: str, year: int) -> list[Event]:
        """Delegate season fetching entirely to the injected source."""
        return await self._source.get_season(year)
