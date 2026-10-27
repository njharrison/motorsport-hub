"""Abstract base class for motorsport data providers."""

from abc import ABC, abstractmethod

from motorsport_calendar.models import Championship, Event


class Provider(ABC):
    """Fetches motorsport data from a remote source.

    Implement this class to add a new data provider (e.g. Ergast, OpenF1, Jolpica).
    Each provider is responsible for mapping its own data format to the shared models.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique provider slug (e.g. 'ergast', 'openf1')."""
        ...

    @property
    @abstractmethod
    def supported_championships(self) -> list[str]:
        """List of championship IDs this provider can supply (e.g. ['formula1'])."""
        ...

    @abstractmethod
    async def fetch_championship(self, championship_id: str, year: int) -> Championship:
        """Fetch the full championship calendar for a given year.

        Args:
            championship_id: Championship slug (e.g. 'formula1').
            year: Season year (e.g. 2025).

        Returns:
            A Championship with all events populated.

        Raises:
            NotImplementedError: Must be implemented by subclasses.
            httpx.HTTPError: On network failures.
        """
        ...

    @abstractmethod
    async def fetch_events(self, championship_id: str, year: int) -> list[Event]:
        """Fetch all individual session events for a championship season.

        Args:
            championship_id: Championship slug.
            year: Season year.

        Returns:
            Flat list of Event objects (one per session, not one per race weekend).
        """
        ...
