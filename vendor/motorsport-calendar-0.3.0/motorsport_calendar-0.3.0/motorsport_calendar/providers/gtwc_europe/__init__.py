"""GT World Challenge Europe provider — pluggable sources, no download logic in the provider."""

from motorsport_calendar.core.registry import registry

from .provider import GtwcEuropeProvider
from .source import GtwcEuropeSource

__all__ = ["GtwcEuropeProvider", "GtwcEuropeSource"]


def _make_provider(source: GtwcEuropeSource) -> GtwcEuropeProvider:
    """Factory GT World Challenge Europe : enveloppe une source dans un GtwcEuropeProvider."""
    return GtwcEuropeProvider(source)


registry.register("gtwc-europe", _make_provider)
