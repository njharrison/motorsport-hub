"""Circuit data for FIA WEC, sourced from fiawec.com's own JSON-LD.

Unlike ``aco_series/circuit_data.py`` (ELMS/MLMC), WEC's JSON-LD
``location`` object includes an ``address`` field consistently formatted
as ``"{city}, {ISO 3166-1 alpha-3 country code}"`` (confirmed empirically,
Sprint 48, across all 8 rounds of the 2026 calendar: "Imola, ITA",
"Sakhir, BHR", "Austin, USA", "Doha, QAT", "Spa-Francorchamps, BEL",
"24 Heures du Mans, FRA", "Sao Paulo, BRA", "Fuji, JPN") — country is
therefore resolved *dynamically* from that code (``WEC_ADDRESS_COUNTRY_CODES``),
the same "prefer live data over a hand-maintained table" reasoning already
used by ``sro_series/circuit_data.py`` for GT World Challenge. The table
below only supplies the one thing the address never gives: an IANA
timezone, plus a fallback country for the (currently never observed) case
of an unmapped or missing address.
"""

from __future__ import annotations

# JSON-LD location.name -> (fallback country, IANA timezone). Country here
# is only used if the address's ISO code isn't in WEC_ADDRESS_COUNTRY_CODES
# below — the address itself is preferred whenever it resolves.
WEC_CIRCUIT_DATA: dict[str, tuple[str, str]] = {
    "Imola": ("Italy", "Europe/Rome"),
    "24 Heures du Mans": ("France", "Europe/Paris"),
    "Fuji Speedway": ("Japan", "Asia/Tokyo"),
    "Circuit international de Sakhir": ("Bahrain", "Asia/Bahrain"),
    "Circuit des Amériques": ("USA", "America/Chicago"),
    "Lusail International Circuit": ("Qatar", "Asia/Qatar"),
    "Interlagos": ("Brazil", "America/Sao_Paulo"),
    "Spa-Francorchamps": ("Belgium", "Europe/Brussels"),
}

# ISO 3166-1 alpha-3 -> English country name (matching the spelling already
# used across this project's other circuit tables and
# gui/event_display.py's _COUNTRY_LABELS keys). Not exhaustive — only codes
# observed on the WEC calendar; extend as new circuits appear (same
# convention as every other "not exhaustive" table in this project).
WEC_ADDRESS_COUNTRY_CODES: dict[str, str] = {
    "ITA": "Italy",
    "FRA": "France",
    "JPN": "Japan",
    "BHR": "Bahrain",
    "USA": "USA",
    "QAT": "Qatar",
    "BRA": "Brazil",
    "BEL": "Belgium",
    "GBR": "United Kingdom",
}
