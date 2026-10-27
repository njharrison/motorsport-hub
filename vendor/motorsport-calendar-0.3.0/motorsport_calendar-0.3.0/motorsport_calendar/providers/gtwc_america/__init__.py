"""GT World Challenge America provider — pluggable sources, no download logic in the provider."""

from motorsport_calendar.core.registry import registry

from .provider import GtwcAmericaProvider
from .source import GtwcAmericaSource

__all__ = ["GtwcAmericaProvider", "GtwcAmericaSource"]


def _make_provider(source: GtwcAmericaSource) -> GtwcAmericaProvider:
    """Factory GT World Challenge America : enveloppe une source dans un GtwcAmericaProvider."""
    return GtwcAmericaProvider(source)


registry.register("gtwc-america", _make_provider)
