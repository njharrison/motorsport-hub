"""OfficialWecSource — fetches from fiawec.com's own JSON-LD (Sprint 48).

Implemented once Sprint 48 confirmed fiawec.com runs on the *same* ACO CMS
as europeanlemansseries.com/lemanscup.com (ELMS/MLMC, Sprint 35): every
race detail page embeds an identical schema.org ``SportsEvent``/
``subEvent`` JSON-LD block. Kept registered under the historical
``"official"`` source name (``ProvidersConfig.wec`` defaults to
``source="official"`` — renaming the registry key would silently break
every existing config relying on that default; "official" also remains an
accurate description, fiawec.com genuinely being the official FIA WEC
website, JSON-LD scraping notwithstanding).

Delegates all HTTP, cache, season/race-page fetching, and generic
label -> SessionType mapping to ``AcoSportsEventSource``. Only WEC-specific
divergences are overridden here — the base class was extended (not
duplicated) for anything reusable by a future fourth ACO-CMS series:

- ``_LABEL_RULES`` (base class) gained "Free Practice 4" (Le Mans' extra
  night practice, mapped to the generic ``FREE_PRACTICE`` type), "Hyperpole"
  (WEC's own qualifying-adjacent shootout — the domain model already has
  ``SessionType.HYPERPOLE`` for it) and "Warm-up" (mapped to ``TEST``, the
  closest existing type). None of these labels ever appear in ELMS/MLMC's
  JSON-LD — purely additive to the shared base.
- ``_EXCLUDED_SLUG_KEYWORDS`` (base class) gained "prologue" — WEC's own
  pre-season test event (``official-prologue-imola-2026``), whose session
  labels ("MORNING SESSION"/"AFTERNOON SESSION") don't match any
  ``_LABEL_RULES`` entry anyway, but excluding the slug keeps round
  numbering limited to real championship rounds, consistent with how
  ELMS/MLMC already exclude their own pre-season tests.
- ``_race_url_belongs_to_season`` (overridden): unlike ELMS/MLMC,
  fiawec.com's ``/en/season/{year}`` page lists *both* the requested year's
  races and next year's (confirmed empirically: fetching ``season/2026``
  returns both ``-2026`` and ``-2027`` suffixed race slugs on the same
  page) — filtered here by the URL's own year suffix.
- ``_build_circuit`` (overridden): country is resolved from the JSON-LD
  ``location.address`` field (``"{city}, {ISO 3166-1 alpha-3 code}"`` —
  see ``wec/circuit_data.py``) rather than a static per-venue table, the
  same "prefer live data" reasoning already used by
  ``sro_series/circuit_data.py``. Falls back to the static
  ``WEC_CIRCUIT_DATA`` table only for an unmapped/missing address.
- ``_race_session_end`` (overridden): the base class's default (trust the
  event-level ``endDate`` when plausible) does not work for WEC — verified
  empirically (Sprint 48) that ``endDate`` is *always* midnight of the
  event's last announced day, unrelated to the race's actual finish time
  (for a 6-hour race this coincidentally looks "implausible" and is
  correctly rejected by the base class's own sanity check; for the 24
  Hours of Le Mans it coincidentally looks "plausible" at ~8 hours and
  would silently produce a badly wrong duration if left unoverridden).
  Race duration is instead parsed from the event's own name (every WEC
  race but two is literally named "X Hours of Y"), with the two
  exceptions ("Lone Star Le Mans", "Qatar 1812km") hardcoded from their
  publicly documented durations (6h and 10h respectively — see
  docs/DATA_SOURCES.md for sources).

See docs/DATA_SOURCES.md for the full investigation and ADR-039 for the
architectural rationale.
"""

from __future__ import annotations

from datetime import datetime, timedelta
import re
from typing import Any

from motorsport_calendar.models import Championship, ChampionshipCategory, Circuit
from motorsport_calendar.providers.aco_series.sports_event_base import AcoSportsEventSource
from motorsport_calendar.providers.wec.circuit_data import (
    WEC_ADDRESS_COUNTRY_CODES,
    WEC_CIRCUIT_DATA,
)
from motorsport_calendar.providers.wec.source import WecSource

__all__ = ["OfficialWecSource"]

_HOURS_PATTERN = re.compile(r"(\d+)\s*Hours?", re.IGNORECASE)

# Named races whose title doesn't contain a parseable "X Hours" pattern —
# durations confirmed via fiawec.com/Wikipedia (Sprint 48), not guessed.
_NAMED_RACE_DURATION_HOURS: dict[str, int] = {
    "Lone Star Le Mans": 6,
    "Qatar 1812km": 10,
}
# Fallback when a future race name matches neither the regex nor the table
# above — 6 hours is WEC's single most common race format.
_DEFAULT_RACE_DURATION_HOURS = 6


class OfficialWecSource(AcoSportsEventSource, WecSource):
    """WEC source backed by fiawec.com's JSON-LD.

    Inherits all HTTP, cache, HTML-parsing and session-merging logic from
    ``AcoSportsEventSource``; overrides only what genuinely differs from
    ELMS/MLMC (see module docstring).
    """

    @property
    def _series_key(self) -> str:
        return "wec"

    @property
    def _base_url(self) -> str:
        return "https://www.fiawec.com"

    @property
    def _event_name_prefix(self) -> str:
        return "WEC"

    @property
    def _circuit_data(self) -> dict[str, tuple[str, str]]:
        return WEC_CIRCUIT_DATA

    def _make_championship(self, year: int) -> Championship:
        return Championship(
            id=f"wec-{year}",
            name="FIA World Endurance Championship",
            category=ChampionshipCategory.ENDURANCE,
        )

    def _race_url_belongs_to_season(self, url: str, year: int) -> bool:
        return url.rstrip("/").endswith(f"-{year}")

    def _build_circuit(self, data: dict[str, Any]) -> Circuit:
        location = data.get("location") or {}
        location_name: str = location.get("name", "Unknown")
        address: str = location.get("address") or ""
        code = address.rsplit(",", 1)[-1].strip() if "," in address else ""
        fallback_country, timezone = self._circuit_data.get(location_name, ("Unknown", "UTC"))
        country = WEC_ADDRESS_COUNTRY_CODES.get(code, fallback_country)
        circuit_id = re.sub(r"[^a-z0-9]+", "-", location_name.lower()).strip("-") or "unknown"
        return Circuit(
            id=f"{self._series_key}-{circuit_id}",
            name=location_name,
            city=location_name,
            country=country,
            timezone=timezone,
        )

    def _race_session_end(
        self, first_start: datetime, event_end: datetime | None, event_name: str
    ) -> datetime | None:
        match = _HOURS_PATTERN.search(event_name)
        if match is not None:
            hours = int(match.group(1))
        else:
            hours = next(
                (h for name, h in _NAMED_RACE_DURATION_HOURS.items() if name in event_name),
                _DEFAULT_RACE_DURATION_HOURS,
            )
        return first_start + timedelta(hours=hours)
