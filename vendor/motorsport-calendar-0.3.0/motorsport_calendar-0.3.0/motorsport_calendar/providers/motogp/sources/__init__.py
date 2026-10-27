"""Concrete MotoGpSource implementations — auto-registration dans SourceRegistry."""

from motorsport_calendar.core.source_registry import source_registry

from .pulselive import PulseliveSource

__all__ = ["PulseliveSource"]

source_registry.register(
    "motogp",
    "pulselive",
    lambda cache, refresh: PulseliveSource(cache=cache, refresh=refresh),
)
