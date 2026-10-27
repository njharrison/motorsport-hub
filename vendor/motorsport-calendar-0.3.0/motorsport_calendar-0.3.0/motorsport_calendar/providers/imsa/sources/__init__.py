"""IMSA data sources — auto-registration dans SourceRegistry."""

from motorsport_calendar.core.source_registry import source_registry

from .official import OfficialImsaSource

__all__ = ["OfficialImsaSource"]

# OfficialImsaSource est un stub (get_season lève NotImplementedError).
# Elle est enregistrée pour permettre la découverte et le futur wiring.
source_registry.register(
    "imsa",
    "official",
    lambda cache, refresh: OfficialImsaSource(),
)
