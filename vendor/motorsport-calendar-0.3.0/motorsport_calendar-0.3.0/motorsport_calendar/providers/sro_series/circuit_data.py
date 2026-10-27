"""Shared circuit data for SRO-organised GT series sharing the same web platform.

GT World Challenge Europe, GT World Challenge America, GT World Challenge Asia
and the Intercontinental GT Challenge (IGTC) are all organised by SRO
Motorsports Group and run on the same CMS (confirmed empirically, Sprint 37:
identical ``/event/{id}/{slug}`` URL scheme and identical HTML markup across
all four ``.com`` sites). A venue's URL slug is stable across series — e.g.
``crowdstrike-24-hours-of-spa`` identifies the same physical circuit whether
scraped from gt-world-challenge-europe.com or intercontinentalgtchallenge.com
— so one shared table, keyed by slug, avoids duplicating it per provider.

Country is *not* looked up here — every event page's ``<title>`` already
states it directly and consistently (e.g. "Misano, Italy, 17 - 19 July
2026"), which is more accurate than a hand-maintained table. Only the clean
circuit name and IANA timezone are kept here, since neither is reliably
present in the scraped pages (the on-page address block is inconsistently
formatted, and only one of the four sites ever exposes an IANA zone name,
in its local-time column header).
"""

from __future__ import annotations

# slug -> (clean circuit name, IANA timezone)
SRO_CIRCUIT_DATA: dict[str, tuple[str, str]] = {
    # GT World Challenge Europe
    "circuit-paul-ricard": ("Circuit Paul Ricard", "Europe/Paris"),
    "brands-hatch": ("Brands Hatch", "Europe/London"),
    "monza": ("Autodromo Nazionale Monza", "Europe/Rome"),
    "crowdstrike-24-hours-of-spa": ("Spa-Francorchamps", "Europe/Brussels"),
    "misano": ("Misano World Circuit", "Europe/Rome"),
    "magny-cours": ("Circuit de Nevers Magny-Cours", "Europe/Paris"),
    "nürburgring": ("Nürburgring", "Europe/Berlin"),
    "zandvoort": ("Circuit Zandvoort", "Europe/Amsterdam"),
    "barcelona": ("Circuit de Barcelona-Catalunya", "Europe/Madrid"),
    "portimao": ("Autódromo Internacional do Algarve", "Europe/Lisbon"),
    # GT World Challenge America
    "sonoma-raceway": ("Sonoma Raceway", "America/Los_Angeles"),
    "circuit-of-the-americas": ("Circuit of the Americas", "America/Chicago"),
    "sebring-international-raceway": ("Sebring International Raceway", "America/New_York"),
    "road-atlanta": ("Road Atlanta", "America/New_York"),
    "road-america": ("Road America", "America/Chicago"),
    "barber-motorsports-park": ("Barber Motorsports Park", "America/Chicago"),
    "indianpolis-8-hour": ("Indianapolis Motor Speedway", "America/New_York"),
    "miami-gt-opening-drive": ("Homestead-Miami Speedway", "America/New_York"),
    # GT World Challenge Asia
    "sepang": ("Sepang International Circuit", "Asia/Kuala_Lumpur"),
    "pertamina-mandalika-international-circuit": (
        "Pertamina Mandalika International Circuit",
        "Asia/Makassar",
    ),
    "fuji-international-speedway": ("Fuji Speedway", "Asia/Tokyo"),
    "beijing-street-circuit": ("Beijing Street Circuit", "Asia/Shanghai"),
    "okayama-international-circuit": ("Okayama International Circuit", "Asia/Tokyo"),
    "shanghai-international-circuit": ("Shanghai International Circuit", "Asia/Shanghai"),
    # Intercontinental GT Challenge
    "bathurst-12-hour": ("Mount Panorama Circuit", "Australia/Sydney"),
    "adac-ravenol-24h-nuerburgring": ("Nürburgring Nordschleife", "Europe/Berlin"),
    "suzuka-1000km": ("Suzuka Circuit", "Asia/Tokyo"),
}
