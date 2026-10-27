"""Concrete GtwcEuropeSource implementations — auto-registration dans SourceRegistry."""

from motorsport_calendar.core.source_registry import source_registry

from .sro_scraper import SroScraperSource

__all__ = ["SroScraperSource"]

source_registry.register(
    "gtwc-europe",
    "sro_scraper",
    lambda cache, refresh: SroScraperSource(cache=cache, refresh=refresh),
)
