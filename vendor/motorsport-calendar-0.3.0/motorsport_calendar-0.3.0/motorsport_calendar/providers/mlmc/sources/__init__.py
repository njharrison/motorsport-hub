"""Concrete MlmcSource implementations — auto-registration dans SourceRegistry."""

from motorsport_calendar.core.source_registry import source_registry

from .aco_scraper import AcoScraperSource

__all__ = ["AcoScraperSource"]

source_registry.register(
    "mlmc",
    "aco_scraper",
    lambda cache, refresh: AcoScraperSource(cache=cache, refresh=refresh),
)
