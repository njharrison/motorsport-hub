"""Moto2Source — abstract contract for all Moto2 data sources."""

from abc import ABC, abstractmethod

from motorsport_calendar.models import Event


class Moto2Source(ABC):
    """Provides raw Moto2 season data.

    Implement this class to add a new data origin for Moto2 calendar data.
    The source is responsible only for fetching and mapping data; it has no
    knowledge of the Provider or the Exporter.
    """

    @abstractmethod
    async def get_season(self, year: int) -> list[Event]:
        """Return all events for the given Moto2 season.

        Args:
            year: The championship year (e.g. 2026).

        Returns:
            Flat list of Event objects, one per round. Sessions (FP1, FP2,
            FP3, Qualifying, Race) are nested inside each Event.
        """
        ...
