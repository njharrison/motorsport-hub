"""IgtcSource — abstract contract for all Intercontinental GT Challenge data sources."""

from abc import ABC, abstractmethod

from motorsport_calendar.models import Event


class IgtcSource(ABC):
    """Provides raw Intercontinental GT Challenge season data.

    Implement this class to add a new data origin for Intercontinental GT
    Challenge calendar data. The source is responsible only for fetching
    and mapping data; it has no knowledge of the Provider or the Exporter.
    """

    @abstractmethod
    async def get_season(self, year: int) -> list[Event]:
        """Return all events for the given Intercontinental GT Challenge season.

        Args:
            year: The championship year (e.g. 2026).

        Returns:
            Flat list of Event objects, one per round. Sessions (FP1, FP2,
            FP3, Qualifying, Race) are nested inside each Event.
        """
        ...
