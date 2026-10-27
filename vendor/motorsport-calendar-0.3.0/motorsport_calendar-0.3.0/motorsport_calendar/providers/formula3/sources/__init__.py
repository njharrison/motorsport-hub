"""Concrete Formula3Source implementations — auto-registration dans SourceRegistry."""

from motorsport_calendar.core.source_registry import source_registry

from .f1calendar import F1CalendarSource

__all__ = ["F1CalendarSource"]

source_registry.register(
    "formula3",
    "f1calendar",
    lambda cache, refresh: F1CalendarSource(cache=cache, refresh=refresh),
)
