"""GtwcAsiaSource — abstract contract for all GT World Challenge Asia data sources."""

from abc import ABC, abstractmethod

from motorsport_calendar.models import Event


class GtwcAsiaSource(ABC):
    """Provides raw GT World Challenge Asia season data.

    Implement this class to add a new data origin for GT World Challenge
    Asia calendar data. The source is responsible only for fetching and
    mapping data; it has no knowledge of the Provider or the Exporter.
    """

    @abstractmethod
    async def get_season(self, year: int) -> list[Event]:
        """Return all events for the given GT World Challenge Asia season.

        Args:
            year: The championship year (e.g. 2026).

        Returns:
            Flat list of Event objects, one per round. Sessions (FP1, FP2,
            Qualifying/Sprint Qualifying, Race/Sprint) are nested inside
            each Event.
        """
        ...
