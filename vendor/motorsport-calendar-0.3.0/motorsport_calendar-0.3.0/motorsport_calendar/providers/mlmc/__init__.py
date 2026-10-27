"""MLMC provider — pluggable sources, no download logic in the provider."""

from motorsport_calendar.core.registry import registry

from .provider import MlmcProvider
from .source import MlmcSource

__all__ = ["MlmcProvider", "MlmcSource"]


def _make_provider(source: MlmcSource) -> MlmcProvider:
    """Factory MLMC : enveloppe une source dans un MlmcProvider."""
    return MlmcProvider(source)


registry.register("mlmc", _make_provider)
