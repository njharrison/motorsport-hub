"""F1 Academy provider — pluggable sources, no download logic in the provider."""

from motorsport_calendar.core.registry import registry

from .provider import F1AcademyProvider
from .source import F1AcademySource

__all__ = ["F1AcademyProvider", "F1AcademySource"]


def _make_provider(source: F1AcademySource) -> F1AcademyProvider:
    """Factory F1 Academy : enveloppe une source dans un F1AcademyProvider."""
    return F1AcademyProvider(source)


registry.register("f1-academy", _make_provider)
