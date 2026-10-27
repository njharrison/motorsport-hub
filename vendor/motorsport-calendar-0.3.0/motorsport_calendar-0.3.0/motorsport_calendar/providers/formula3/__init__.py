"""Formula 3 provider — pluggable sources, no download logic in the provider."""

from motorsport_calendar.core.registry import registry

from .provider import Formula3Provider
from .source import Formula3Source

__all__ = ["Formula3Provider", "Formula3Source"]


def _make_provider(source: Formula3Source) -> Formula3Provider:
    """Factory Formula 3 : enveloppe une source dans un Formula3Provider."""
    return Formula3Provider(source)


registry.register("formula3", _make_provider)
