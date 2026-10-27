"""FormulaESource — abstract contract for all Formula E data sources."""

from abc import ABC, abstractmethod

from motorsport_calendar.models import Event


class FormulaESource(ABC):
    """Provides raw Formula E season data.

    Implement this class to add a new data origin for Formula E calendar data.
    The source is responsible only for fetching and mapping data; it has
    no knowledge of the Provider or the Exporter.
    """

    @abstractmethod
    async def get_season(self, year: int) -> list[Event]:
        """Return all events for the given Formula E season.

        Args:
            year: The championship year (e.g. 2025).

        Returns:
            Flat list of Event objects, one per E-Prix round. Formula E
            splits double-header weekends into two separate rounds (each
            with its own round number), unlike F1 Academy's single-event
            triple-header — so no session-key collision handling is needed.
        """
        ...
