"""Moto2 provider — pluggable sources, no download logic in the provider."""

from motorsport_calendar.core.registry import registry

from .provider import Moto2Provider
from .source import Moto2Source

__all__ = ["Moto2Provider", "Moto2Source"]


def _make_provider(source: Moto2Source) -> Moto2Provider:
    """Factory Moto2 : enveloppe une source dans un Moto2Provider."""
    return Moto2Provider(source)


registry.register("moto2", _make_provider)
