"""Abstract base class for calendar exporters."""

from abc import ABC, abstractmethod
from collections.abc import Iterable
from pathlib import Path

from motorsport_calendar.models import Event


class Exporter(ABC):
    """Serialises a collection of events to a specific calendar file format.

    Implement this class to add a new output format (e.g. ICS, JSON, CSV).
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique exporter slug (e.g. 'ics', 'json')."""
        ...

    @property
    @abstractmethod
    def file_extension(self) -> str:
        """File extension without leading dot (e.g. 'ics', 'json')."""
        ...

    @abstractmethod
    def export(self, events: Iterable[Event], output_path: Path) -> None:
        """Write the events to a file.

        Args:
            events: Events to export (each Event contains its Sessions).
            output_path: Destination file path.

        Raises:
            OSError: On file write failures.
        """
        ...

    @abstractmethod
    def export_to_string(self, events: Iterable[Event]) -> str:
        """Serialise the events to a string (useful for testing/streaming).

        Args:
            events: Events to export.

        Returns:
            The serialised calendar as a string.
        """
        ...
