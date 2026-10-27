"""MlmcSource — abstract contract for all Michelin Le Mans Cup data sources."""

from abc import ABC, abstractmethod

from motorsport_calendar.models import Event


class MlmcSource(ABC):
    """Provides raw Michelin Le Mans Cup season data.

    Implement this class to add a new data origin for MLMC calendar data.
    The source is responsible only for fetching and mapping data; it has
    no knowledge of the Provider or the Exporter.

    Road to Le Mans (run during the 24 Heures du Mans week) is listed as
    just another round on the same season page — it is not a separate
    championship_id, matching how the site itself presents it (see
    docs/DATA_SOURCES.md's original recommendation, confirmed correct).
    """

    @abstractmethod
    async def get_season(self, year: int) -> list[Event]:
        """Return all events for the given MLMC season (including Road to
        Le Mans, if present that year).

        Args:
            year: The championship year (e.g. 2026).

        Returns:
            Flat list of Event objects, one per round. Sessions (FP1, FP2,
            Bronze Driver Test, Qualifying, Race) are nested inside each
            Event.
        """
        ...
