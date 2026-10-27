"""Shared circuit data for ACO endurance series sharing the same venues.

ELMS and Michelin Le Mans Cup are co-located at the same six 2026 venues
(confirmed empirically, Sprint 35: identical ``location.name`` values in
both sites' JSON-LD). One shared table avoids duplicating it per provider —
this is not anticipatory factoring, the co-location is a fact of the
calendar, not a guess.

Keyed by the JSON-LD ``location.name`` value -> (country, IANA timezone).
"""

from __future__ import annotations

ACO_CIRCUIT_DATA: dict[str, tuple[str, str]] = {
    "Barcelona": ("Spain", "Europe/Madrid"),
    "Paul Ricard": ("France", "Europe/Paris"),
    "Imola": ("Italy", "Europe/Rome"),
    "Spa-Francorchamps": ("Belgium", "Europe/Brussels"),
    "Silverstone": ("United Kingdom", "Europe/London"),
    "Autódromo Internacional do Algarve": ("Portugal", "Europe/Lisbon"),
    "Le Mans": ("France", "Europe/Paris"),
}
