"""Formula E provider — pluggable sources, no download logic in the provider."""

from motorsport_calendar.core.registry import registry

from .provider import FormulaEProvider
from .source import FormulaESource

__all__ = ["FormulaEProvider", "FormulaESource"]


def _make_provider(source: FormulaESource) -> FormulaEProvider:
    """Factory Formula E : enveloppe une source dans un FormulaEProvider."""
    return FormulaEProvider(source)


registry.register("formula-e", _make_provider)
