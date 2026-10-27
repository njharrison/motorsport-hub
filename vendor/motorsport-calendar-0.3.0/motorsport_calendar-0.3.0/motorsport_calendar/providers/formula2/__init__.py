"""Formula 2 provider — pluggable sources, no download logic in the provider."""

from motorsport_calendar.core.registry import registry

from .provider import Formula2Provider
from .source import Formula2Source

__all__ = ["Formula2Provider", "Formula2Source"]


def _make_provider(source: Formula2Source) -> Formula2Provider:
    """Factory Formula 2 : enveloppe une source dans un Formula2Provider."""
    return Formula2Provider(source)


registry.register("formula2", _make_provider)
