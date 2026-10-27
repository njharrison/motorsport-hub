"""ELMS provider — pluggable sources, no download logic in the provider."""

from motorsport_calendar.core.registry import registry

from .provider import ElmsProvider
from .source import ElmsSource

__all__ = ["ElmsProvider", "ElmsSource"]


def _make_provider(source: ElmsSource) -> ElmsProvider:
    """Factory ELMS : enveloppe une source dans un ElmsProvider."""
    return ElmsProvider(source)


registry.register("elms", _make_provider)
