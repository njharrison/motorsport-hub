"""GT World Challenge Asia provider — pluggable sources, no download logic in the provider."""

from motorsport_calendar.core.registry import registry

from .provider import GtwcAsiaProvider
from .source import GtwcAsiaSource

__all__ = ["GtwcAsiaProvider", "GtwcAsiaSource"]


def _make_provider(source: GtwcAsiaSource) -> GtwcAsiaProvider:
    """Factory GT World Challenge Asia : enveloppe une source dans un GtwcAsiaProvider."""
    return GtwcAsiaProvider(source)


registry.register("gtwc-asia", _make_provider)
