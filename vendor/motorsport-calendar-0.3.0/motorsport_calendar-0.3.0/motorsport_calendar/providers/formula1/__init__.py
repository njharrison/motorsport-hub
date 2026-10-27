"""Formula 1 provider — pluggable sources, no download logic in the provider."""

from motorsport_calendar.core.registry import registry

from .provider import Formula1Provider
from .source import Formula1Source

__all__ = ["Formula1Provider", "Formula1Source"]


def _make_provider(source: Formula1Source) -> Formula1Provider:
    """Factory Formula 1 : enveloppe une source dans un Formula1Provider."""
    return Formula1Provider(source)


registry.register("formula1", _make_provider)
