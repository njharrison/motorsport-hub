"""PulseliveSource — Moto2 source scraped from Dorna's official pulselive API.

Delegates all HTTP, cache, JSON parsing and session-mapping logic to
PulseliveGpSource. Only Moto2-specific configuration (category acronym, race
duration, championship) lives here — the season fetch and event parsing are
shared with MotoGP/Moto3 (confirmed same event/round list, same API, see
``motogp_series/pulselive_base.py`` module docstring).

Source: https://api.pulselive.motogp.com/motogp/v1/events?seasonYear={year}
(official, unauthenticated Dorna Sports API — same endpoint as MotoGP, the
``broadcasts`` array already covers all classes; filtered here to the
``MT2`` category acronym).
"""

from __future__ import annotations

from motorsport_calendar.models import Championship, ChampionshipCategory
from motorsport_calendar.providers.moto2.source import Moto2Source
from motorsport_calendar.providers.motogp_series.pulselive_base import PulseliveGpSource

__all__ = ["PulseliveSource"]


class PulseliveSource(PulseliveGpSource, Moto2Source):
    """Moto2 source backed by Dorna's official pulselive API.

    Inherits all HTTP, cache, JSON-parsing and session-mapping logic from
    PulseliveGpSource. The three members below are the only Moto2-specific
    configuration.
    """

    @property
    def _series_key(self) -> str:
        return "moto2"

    @property
    def _category_acronym(self) -> str:
        return "MT2"

    @property
    def _race_duration_minutes(self) -> int:
        return 40

    def _make_championship(self, year: int) -> Championship:
        return Championship(
            id=f"moto2-{year}",
            name="Moto2",
            category=ChampionshipCategory.MOTORBIKE,
        )
