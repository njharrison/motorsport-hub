"""F1AcademySource — abstract contract for all F1 Academy data sources."""

from abc import ABC, abstractmethod

from motorsport_calendar.models import Event


class F1AcademySource(ABC):
    """Provides raw F1 Academy season data.

    Implement this class to add a new data origin for F1 Academy calendar data.
    The source is responsible only for fetching and mapping data; it has
    no knowledge of the Provider or the Exporter.
    """

    @abstractmethod
    async def get_season(self, year: int) -> list[Event]:
        """Return all events for the given F1 Academy season.

        Args:
            year: The championship year (e.g. 2025).

        Returns:
            Flat list of Event objects, one per race weekend.
            Sessions (FP1, FP2, Qualifying, Race 1/2/3) are nested
            inside each Event.
        """
        ...
