"""IMSA provider — pluggable sources, no download logic in the provider."""

from motorsport_calendar.core.registry import registry

from .provider import ImsaProvider
from .source import ImsaSource

__all__ = ["ImsaProvider", "ImsaSource"]


def _make_provider(source: ImsaSource) -> ImsaProvider:
    """Factory IMSA : enveloppe une source dans un ImsaProvider."""
    return ImsaProvider(source)


registry.register("imsa", _make_provider)
