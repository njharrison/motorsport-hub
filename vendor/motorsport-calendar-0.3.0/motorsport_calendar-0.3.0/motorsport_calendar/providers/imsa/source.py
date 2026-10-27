"""ImsaSource — abstract contract for all IMSA data sources."""

from abc import ABC, abstractmethod

from motorsport_calendar.models import Event


class ImsaSource(ABC):
    """Provides raw IMSA WeatherTech SportsCar Championship season data.

    Implement this class to add a new data origin (official API, scraper,
    cache, etc.). The source is responsible only for fetching and mapping
    data; it has no knowledge of the Provider or the Exporter.
    """

    @abstractmethod
    async def get_season(self, year: int) -> list[Event]:
        """Return all events for the given IMSA season.

        Args:
            year: The championship year (e.g. 2026).

        Returns:
            Flat list of Event objects, one per race weekend.
            Sessions (typically Practice 1/2/3, Qualifying, Race) are
            nested inside each Event.

        Raises:
            NotImplementedError: Must be implemented by subclasses.
        """
        ...
