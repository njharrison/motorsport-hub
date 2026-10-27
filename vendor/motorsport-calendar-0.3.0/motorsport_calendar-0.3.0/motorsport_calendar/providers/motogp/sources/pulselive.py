"""PulseliveSource — MotoGP source scraped from Dorna's official pulselive API.

Delegates all HTTP, cache, JSON parsing and session-mapping logic to
PulseliveGpSource. Only MotoGP-specific configuration (category acronym,
race duration, championship) lives here — the season fetch and event
parsing are shared with Moto2/Moto3 (confirmed same event/round list, same
API, see ``motogp_series/pulselive_base.py`` module docstring).

Source: https://api.pulselive.motogp.com/motogp/v1/events?seasonYear={year}
(official, unauthenticated Dorna Sports API).
"""

from __future__ import annotations

from motorsport_calendar.models import Championship, ChampionshipCategory
from motorsport_calendar.providers.motogp.source import MotoGpSource
from motorsport_calendar.providers.motogp_series.pulselive_base import PulseliveGpSource

__all__ = ["PulseliveSource"]


class PulseliveSource(PulseliveGpSource, MotoGpSource):
    """MotoGP source backed by Dorna's official pulselive API.

    Inherits all HTTP, cache, JSON-parsing and session-mapping logic from
    PulseliveGpSource. The three members below are the only MotoGP-specific
    configuration.
    """

    @property
    def _series_key(self) -> str:
        return "motogp"

    @property
    def _category_acronym(self) -> str:
        return "MGP"

    @property
    def _race_duration_minutes(self) -> int:
        return 45

    def _make_championship(self, year: int) -> Championship:
        return Championship(
            id=f"motogp-{year}",
            name="MotoGP",
            category=ChampionshipCategory.MOTORBIKE,
        )
