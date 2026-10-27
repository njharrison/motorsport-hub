"""WEC data sources — auto-registration dans SourceRegistry."""

from motorsport_calendar.core.source_registry import source_registry

from .official import OfficialWecSource

__all__ = ["OfficialWecSource"]

# OfficialWecSource est un stub (get_season lève NotImplementedError).
# Elle est enregistrée pour permettre la découverte et le futur wiring.
source_registry.register(
    "wec",
    "official",
    lambda cache, refresh: OfficialWecSource(),
)
