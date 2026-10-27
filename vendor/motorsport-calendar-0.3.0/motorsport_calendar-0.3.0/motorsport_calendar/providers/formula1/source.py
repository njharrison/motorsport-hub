"""Formula1Source — abstract contract for all F1 data sources."""

from abc import ABC, abstractmethod

from motorsport_calendar.models import Event


class Formula1Source(ABC):
    """Provides raw F1 season data.

    Implement this class to add a new data origin (official API, OpenF1,
    Ergast, cache, etc.). The source is responsible only for fetching and
    mapping data; it has no knowledge of the Provider or the Exporter.
    """

    @abstractmethod
    async def get_season(self, year: int) -> list[Event]:
        """Return all events for the given F1 season.

        Args:
            year: The championship year (e.g. 2025).

        Returns:
            Flat list of Event objects, one per race weekend.
            Sessions (FP1, Qualifying, Race…) are nested inside each Event.

        Raises:
            NotImplementedError: Must be implemented by subclasses.
        """
        ...
