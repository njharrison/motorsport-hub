"""WecSource — abstract contract for all WEC data sources."""

from abc import ABC, abstractmethod

from motorsport_calendar.models import Event


class WecSource(ABC):
    """Provides raw WEC season data.

    Implement this class to add a new data origin (official WEC API, scraper,
    cache, etc.). The source is responsible only for fetching and mapping data;
    it has no knowledge of the Provider or the Exporter.
    """

    @abstractmethod
    async def get_season(self, year: int) -> list[Event]:
        """Return all events for the given WEC season.

        Args:
            year: The championship year (e.g. 2026).

        Returns:
            Flat list of Event objects, one per race weekend.
            Sessions (FREE_PRACTICE, QUALIFYING, HYPERPOLE, RACE) are nested
            inside each Event.

        Raises:
            NotImplementedError: Must be implemented by subclasses.
        """
        ...
