"""IGTC provider — pluggable sources, no download logic in the provider."""

from motorsport_calendar.core.registry import registry

from .provider import IgtcProvider
from .source import IgtcSource

__all__ = ["IgtcProvider", "IgtcSource"]


def _make_provider(source: IgtcSource) -> IgtcProvider:
    """Factory IGTC : enveloppe une source dans un IgtcProvider."""
    return IgtcProvider(source)


registry.register("igtc", _make_provider)
