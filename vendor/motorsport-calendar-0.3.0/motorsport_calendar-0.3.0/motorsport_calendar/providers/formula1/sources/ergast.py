"""ErgastSource — backward-compatibility alias for JolpicaSource.

Ergast was shut down end-2024. JolpicaSource (api.jolpi.ca) is its
Ergast-compatible successor and the canonical implementation.
"""

from motorsport_calendar.providers.formula1.sources.jolpica import JolpicaSource as ErgastSource

__all__ = ["ErgastSource"]
