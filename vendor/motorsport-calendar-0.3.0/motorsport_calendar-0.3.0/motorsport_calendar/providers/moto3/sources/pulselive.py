"""PulseliveSource — Moto3 source scraped from Dorna's official pulselive API.

Delegates all HTTP, cache, JSON parsing and session-mapping logic to
PulseliveGpSource. Only Moto3-specific configuration (category acronym, race
duration, championship) lives here — the season fetch and event parsing are
shared with MotoGP/Moto2 (confirmed same event/round list, same API, see
``motogp_series/pulselive_base.py`` module docstring).

Source: https://api.pulselive.motogp.com/motogp/v1/events?seasonYear={year}
(official, unauthenticated Dorna Sports API — same endpoint as MotoGP, the
``broadcasts`` array already covers all classes; filtered here to the
``MT3`` category acronym).
"""

from __future__ import annotations

from motorsport_calendar.models import Championship, ChampionshipCategory
from motorsport_calendar.providers.moto3.source import Moto3Source
from motorsport_calendar.providers.motogp_series.pulselive_base import PulseliveGpSource

__all__ = ["PulseliveSource"]


class PulseliveSource(PulseliveGpSource, Moto3Source):
    """Moto3 source backed by Dorna's official pulselive API.

    Inherits all HTTP, cache, JSON-parsing and session-mapping logic from
    PulseliveGpSource. The three members below are the only Moto3-specific
    configuration.
    """

    @property
    def _series_key(self) -> str:
        return "moto3"

    @property
    def _category_acronym(self) -> str:
        return "MT3"

    @property
    def _race_duration_minutes(self) -> int:
        return 35

    def _make_championship(self, year: int) -> Championship:
        return Championship(
            id=f"moto3-{year}",
            name="Moto3",
            category=ChampionshipCategory.MOTORBIKE,
        )
