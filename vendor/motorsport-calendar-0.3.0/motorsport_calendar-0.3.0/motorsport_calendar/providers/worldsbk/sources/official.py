"""OfficialWorldSbkSource — fetches from the official WorldSBK data platform.

Not yet implemented. Source investigation (Sprint 38) confirmed WorldSBK
(FIM Superbike World Championship, organised by Dorna Sports since 2022)
runs on the same "Pulse Live" platform family as MotoGP/Moto2/Moto3, but no
publicly reachable API endpoint was found, documented here so the next
attempt does not repeat the same dead ends:

- **No documented public API.**
- **worldsbk.com's calendar/schedule pages are fully client-rendered** — no
  server-rendered HTML table or embedded JSON to scrape (confirmed:
  fetching the calendar and schedule pages directly returns no round/date
  data at all, unlike GT World Challenge's SRO sites, Sprint 37).
- **A candidate API host was found** (``wsbk-api-origin.gplat-test.
  pulselive.com``, referenced as ``window.SD_DOMAIN`` in the site's own
  page source) but it does not respond to external requests — connection
  attempts time out, consistent with an internal/private service not
  exposed to the public internet (and its ``-test`` naming suggests it may
  not even be the production host).
- **MotoGP's own API host** (``api.pulselive.motogp.com``, used by
  ``motogp_series/pulselive_base.py``) does **not** cover WorldSBK — its
  circuit ``timing_ids`` only ever list ``MGP``/``RKC``/``CEV``/``ATC``
  business units, never an SBK-equivalent, confirming it is a genuinely
  separate platform tenant, not a shared multi-series endpoint.
- Several plausible endpoint guesses following MotoGP's own naming
  convention (``/wsbk/v1/events``, ``/sbk/v1/events``, ``/superbike/v1/
  events``, etc., on ``api.pulselive.worldsbk.com``) were tried directly —
  all returned a real (non-generic-gateway) 404 from the app's own backend,
  confirming the host is live but none of the guessed routes exist.

Decision (confirmed with the user): register the full Provider/Source
architecture — exactly like ``OfficialWecSource``/``OfficialImsaSource`` —
so the integration points (registry, wizard, "Ce week-end", categories,
display names, CLI) are validated end-to-end, without guessing at an
undocumented API or adding browser automation (Playwright) to reach a
JS-only calendar widget. See docs/DATA_SOURCES.md for the full
investigation and ADR-029 for the architectural rationale.

Sessions expected once implemented: FP1/FP2, Superpole (qualifying), Race 1,
Superpole Race, Race 2 — WorldSBK's three-race weekend format is distinct
from MotoGP's FP/Q/Sprint/Race shape.
"""

from motorsport_calendar.models import Event
from motorsport_calendar.providers.worldsbk.source import WorldSbkSource


class OfficialWorldSbkSource(WorldSbkSource):
    """Fetches WorldSBK season data from the official Dorna data platform.

    Not yet implemented — see module docstring for the source
    investigation and why no reachable data source was found in Sprint 38.
    """

    async def get_season(self, year: int) -> list[Event]:
        raise NotImplementedError
