"""Moto3 provider — pluggable sources, no download logic in the provider."""

from motorsport_calendar.core.registry import registry

from .provider import Moto3Provider
from .source import Moto3Source

__all__ = ["Moto3Provider", "Moto3Source"]


def _make_provider(source: Moto3Source) -> Moto3Provider:
    """Factory Moto3 : enveloppe une source dans un Moto3Provider."""
    return Moto3Provider(source)


registry.register("moto3", _make_provider)
