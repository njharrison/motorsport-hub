"""Formula3Source — abstract contract for all F3 data sources."""

from abc import ABC, abstractmethod

from motorsport_calendar.models import Event


class Formula3Source(ABC):
    """Provides raw FIA Formula 3 season data.

    Implement this class to add a new data origin for F3 calendar data.
    The source is responsible only for fetching and mapping data; it has
    no knowledge of the Provider or the Exporter.
    """

    @abstractmethod
    async def get_season(self, year: int) -> list[Event]:
        """Return all events for the given F3 season.

        Args:
            year: The championship year (e.g. 2025).

        Returns:
            Flat list of Event objects, one per race weekend.
            Sessions (Free Practice, Qualifying, Sprint Race, Feature Race)
            are nested inside each Event.
        """
        ...
