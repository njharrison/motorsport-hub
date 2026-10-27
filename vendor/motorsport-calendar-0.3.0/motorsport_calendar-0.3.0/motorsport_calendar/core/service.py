"""CalendarService — central orchestrator with no business logic of its own."""

from pathlib import Path

from motorsport_calendar.exporters.base import Exporter
from motorsport_calendar.models import Championship
from motorsport_calendar.providers.base import Provider


class CalendarService:
    """Wires together a Provider and an Exporter to produce a calendar file.

    Usage::

        service = CalendarService()
        service.register_provider(MyProvider())
        service.register_exporter(ICSExporter())
        await service.export_championship("my-provider", "formula1", 2025, "ics", Path("f1.ics"))
    """

    def __init__(self) -> None:
        self._providers: dict[str, Provider] = {}
        self._exporters: dict[str, Exporter] = {}

    # -------------------------------------------------------------------------
    # Registration
    # -------------------------------------------------------------------------

    def register_provider(self, provider: Provider) -> None:
        """Register a data provider."""
        self._providers[provider.name] = provider

    def register_exporter(self, exporter: Exporter) -> None:
        """Register a calendar exporter."""
        self._exporters[exporter.name] = exporter

    # -------------------------------------------------------------------------
    # Introspection
    # -------------------------------------------------------------------------

    @property
    def providers(self) -> list[str]:
        """Names of registered providers."""
        return list(self._providers.keys())

    @property
    def exporters(self) -> list[str]:
        """Names of registered exporters."""
        return list(self._exporters.keys())

    # -------------------------------------------------------------------------
    # Operations
    # -------------------------------------------------------------------------

    async def get_championship(
        self,
        provider_name: str,
        championship_id: str,
        year: int,
    ) -> Championship:
        """Fetch a championship from a named provider.

        Raises:
            KeyError: If the provider is not registered.
        """
        if provider_name not in self._providers:
            raise KeyError(f"Provider '{provider_name}' is not registered.")
        return await self._providers[provider_name].fetch_championship(championship_id, year)

    async def export_championship(
        self,
        provider_name: str,
        championship_id: str,
        year: int,
        exporter_name: str,
        output: Path,
    ) -> None:
        """Fetch a championship's events and write them to a file.

        Raises:
            KeyError: If provider or exporter is not registered.
        """
        if exporter_name not in self._exporters:
            raise KeyError(f"Exporter '{exporter_name}' is not registered.")
        if provider_name not in self._providers:
            raise KeyError(f"Provider '{provider_name}' is not registered.")
        events = await self._providers[provider_name].fetch_events(championship_id, year)
        self._exporters[exporter_name].export(events, output)
