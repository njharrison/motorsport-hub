"""OfficialImsaSource — fetches from the official IMSA data platform.

Not yet implemented. Source investigation (Sprint 36) found no reachable
path to session-level schedule data, documented here so the next attempt
does not repeat the same dead ends:

- **No documented public API.** No official IMSA developer API found.
- **imsa.com is fully blocked at the infrastructure level**, not merely
  scraping-unfriendly: every path tested — homepage, schedule page, news
  articles, and even static PDF assets under ``/wp-content/uploads/`` —
  returns HTTP 403 with an active Cloudflare challenge
  (``cf-mitigated: challenge``). This is a hard block, not a missing-header
  issue; getting past it would require full browser automation
  (Playwright), a much heavier dependency than any other source in this
  project, and closer to actively defeating anti-bot protection than
  scraping — not attempted.
- **IMSA's timing provider is Al Kamel Systems** (same as WEC/ELMS/MLMC —
  ``imsa.results.alkamelcloud.com`` is reachable, unlike imsa.com), but
  that portal is a **post-event results archive**, not a forward-looking
  schedule: session folders (e.g. ``202606261125_Practice 1``) only exist
  *after* a session has run. No usable calendar source there.
- **Wikipedia has a clean, stable schedule table** (official MediaWiki API,
  e.g. page "2026 IMSA SportsCar Championship", section "Schedule"):
  round number, race name, circuit, city, and date — but **no session-level
  times** (no FP1/FP2/Qualifying/Race start times), only race dates and
  race duration. Not enough to build valid ``Session`` objects (which
  require both a start and an end time) without inventing times.
- **Specialist outlets (Sportscar365, 51gt3.com) publish session times**,
  but only as prose inside individual news articles ("qualifying gets
  underway at 3:40 p.m. EST") — not structured data, and 51gt3.com itself
  returned HTTP 403 when tested. Parsing natural-language article text
  reliably across ~11 rounds x several sessions would be fragile and is
  not a "stable, documented source" in the sense this project requires.

Decision (confirmed with the user): register the full Provider/Source
architecture — exactly like ``OfficialWecSource`` — so the integration
points (registry, wizard, "Ce week-end", categories, display names, CLI)
are validated end-to-end, without fabricating session times that no real
source actually provides. See docs/DATA_SOURCES.md for the full
investigation and ADR-027 for the architectural rationale.

Sessions expected once implemented: Practice 1/2(/3), Qualifying, Race —
standard sportscar weekend format, no IMSA-specific SessionType needed
(unlike WEC's Hyperpole).
"""

from motorsport_calendar.models import Event
from motorsport_calendar.providers.imsa.source import ImsaSource


class OfficialImsaSource(ImsaSource):
    """Fetches IMSA season data from the official IMSA data platform.

    Not yet implemented — see module docstring for the source
    investigation and why no reachable data source was found in Sprint 36.
    """

    async def get_season(self, year: int) -> list[Event]:
        raise NotImplementedError
