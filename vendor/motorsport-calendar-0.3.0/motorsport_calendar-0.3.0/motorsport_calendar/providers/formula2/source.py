"""Formula2Source — abstract contract for all F2 data sources."""

from abc import ABC, abstractmethod

from motorsport_calendar.models import Event


class Formula2Source(ABC):
    """Provides raw Formula 2 season data.

    Implement this class to add a new data origin for F2 calendar data.
    The source is responsible only for fetching and mapping data; it has
    no knowledge of the Provider or the Exporter.
    """

    @abstractmethod
    async def get_season(self, year: int) -> list[Event]:
        """Return all events for the given F2 season.

        Args:
            year: The championship year (e.g. 2025).

        Returns:
            Flat list of Event objects, one per race weekend.
            Sessions (FP, Qualifying, Sprint Race, Feature Race) are
            nested inside each Event.
        """
        ...
