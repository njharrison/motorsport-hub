"""WorldSbkSource — abstract contract for all World Superbike data sources."""

from abc import ABC, abstractmethod

from motorsport_calendar.models import Event


class WorldSbkSource(ABC):
    """Provides raw World Superbike (WorldSBK) season data.

    Implement this class to add a new data origin for WorldSBK calendar
    data. The source is responsible only for fetching and mapping data; it
    has no knowledge of the Provider or the Exporter.
    """

    @abstractmethod
    async def get_season(self, year: int) -> list[Event]:
        """Return all events for the given WorldSBK season.

        Args:
            year: The championship year (e.g. 2026).

        Returns:
            Flat list of Event objects, one per round.

        Raises:
            NotImplementedError: Must be implemented by subclasses.
        """
        ...
