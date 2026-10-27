"""FIA WEC provider — pluggable sources, no download logic in the provider."""

from motorsport_calendar.core.registry import registry

from .provider import WecProvider
from .source import WecSource

__all__ = ["WecProvider", "WecSource"]


def _make_provider(source: WecSource) -> WecProvider:
    """Factory WEC : enveloppe une source dans un WecProvider."""
    return WecProvider(source)


registry.register("wec", _make_provider)
