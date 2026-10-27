"""WorldSBK provider — pluggable sources, no download logic in the provider."""

from motorsport_calendar.core.registry import registry

from .provider import WorldSbkProvider
from .source import WorldSbkSource

__all__ = ["WorldSbkProvider", "WorldSbkSource"]


def _make_provider(source: WorldSbkSource) -> WorldSbkProvider:
    """Factory WorldSBK : enveloppe une source dans un WorldSbkProvider."""
    return WorldSbkProvider(source)


registry.register("worldsbk", _make_provider)
