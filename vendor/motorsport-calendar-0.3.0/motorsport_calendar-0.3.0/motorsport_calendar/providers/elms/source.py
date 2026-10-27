"""ElmsSource — abstract contract for all European Le Mans Series data sources."""

from abc import ABC, abstractmethod

from motorsport_calendar.models import Event


class ElmsSource(ABC):
    """Provides raw ELMS season data.

    Implement this class to add a new data origin for ELMS calendar data.
    The source is responsible only for fetching and mapping data; it has
    no knowledge of the Provider or the Exporter.
    """

    @abstractmethod
    async def get_season(self, year: int) -> list[Event]:
        """Return all events for the given ELMS season.

        Args:
            year: The championship year (e.g. 2026).

        Returns:
            Flat list of Event objects, one per round. Sessions (FP1, FP2,
            Bronze Driver Test, Qualifying, Race) are nested inside each
            Event.
        """
        ...
