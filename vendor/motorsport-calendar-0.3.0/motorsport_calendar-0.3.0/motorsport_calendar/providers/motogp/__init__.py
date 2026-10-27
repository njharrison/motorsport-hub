"""MotoGP provider — pluggable sources, no download logic in the provider."""

from motorsport_calendar.core.registry import registry

from .provider import MotoGpProvider
from .source import MotoGpSource

__all__ = ["MotoGpProvider", "MotoGpSource"]


def _make_provider(source: MotoGpSource) -> MotoGpProvider:
    """Factory MotoGP : enveloppe une source dans un MotoGpProvider."""
    return MotoGpProvider(source)


registry.register("motogp", _make_provider)
