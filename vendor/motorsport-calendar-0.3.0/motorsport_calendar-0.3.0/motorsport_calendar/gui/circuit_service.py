"""CircuitService — a queryable circuit database built from events already
loaded in memory (Sprint 47).

Circuits were, until now, plain text on a ChampionshipCard — this module
promotes them to first-class entities: aggregated across every
championship/season already fetched, a circuit becomes something with its
own name, country, list of championships that have raced there, and event
history. No network call here — building the database is purely a local
aggregation over ``year_events``, the exact same dict
``controller.get_calendar_year_events`` already produces and
``search_service.py``/``notification_service.py``/``season_explorer.py``
already consume.

Reuses existing models end-to-end rather than inventing a second
normalization: ``event_display.circuit_display_name``/``normalize_key``/
``resolve_country`` (Sprint 32, ADR-023; promoted to public at Sprint 47)
for a circuit's own name/identity/country, ``display_names.get_display_name``
for championship names — a circuit is never named or grouped differently
here than anywhere else in the app.
"""

from __future__ import annotations

from dataclasses import dataclass

from motorsport_calendar.gui.display_names import get_display_name
from motorsport_calendar.gui.event_display import (
    circuit_display_name,
    normalize_event_display,
    normalize_key,
    resolve_country,
)
from motorsport_calendar.models import Event


@dataclass(frozen=True)
class CircuitEventEntry:
    """One event that took place at a circuit — a single row of its
    history, already sorted chronologically by the service that builds it.

    Carries ``championship_id``/``event_uid`` — identity, never
    interpreted here — so a future click-through (not wired this sprint)
    could look the full ``Event`` back up in ``year_events``, same "carry
    identity, never interpret" pattern as ``SeasonEventRow`` (Sprint 42).
    """

    event_name: str
    championship_id: str
    championship_name: str
    season: int
    event_uid: str


@dataclass(frozen=True)
class CircuitProfile:
    """Everything known about one circuit, aggregated across every
    championship/season already loaded — the "fiche Circuit".

    ``country`` is ``None`` when unknown — never the literal "Unknown"
    (same contract as ``EventDisplayData.country``). ``championship_ids``/
    ``championship_names`` are parallel tuples, both sorted alphabetically
    by championship display name — deterministic order, independent of
    which event happened to be indexed first.
    """

    circuit_key: str
    name: str
    country: str | None
    championship_ids: tuple[str, ...]
    championship_names: tuple[str, ...]
    championship_count: int
    total_events: int
    first_season: int
    last_season: int
    events: tuple[CircuitEventEntry, ...]


class CircuitService:
    """Builds and queries a circuit database from already-fetched events.

    Mirrors ``SearchService``'s own "no state beyond the last built index,
    rebuilt wholesale on demand, no network access, no Flet dependency"
    pattern (Sprint 45).
    """

    def __init__(self) -> None:
        self._circuits: dict[str, CircuitProfile] = {}

    def build_index(self, year_events: dict[str, list[Event]]) -> None:
        """Rebuild the circuit database from already-fetched events.

        Args:
            year_events: registry championship id -> its events for the
                currently loaded year (``controller.get_calendar_year_events``
                — the same dict every other Sprint 44+ compute module
                already consumes). Safe to call as often as the underlying
                data changes; each call replaces the previous index
                wholesale, never appends to it.
        """
        names: dict[str, str] = {}
        countries: dict[str, str | None] = {}
        championship_ids: dict[str, set[str]] = {}
        seasons: dict[str, list[int]] = {}
        events: dict[str, list[CircuitEventEntry]] = {}

        for championship_id, championship_events in year_events.items():
            championship_name = get_display_name(championship_id)
            for event in championship_events:
                key = normalize_key(circuit_display_name(event.circuit))
                if key not in names:
                    # First occurrence wins the display name — same
                    # convention already established for circuit
                    # deduplication in search_service.py (Sprint 45).
                    names[key] = circuit_display_name(event.circuit)
                    countries[key] = None
                    championship_ids[key] = set()
                    seasons[key] = []
                    events[key] = []

                if countries[key] is None:
                    # Best-available-data across providers: one provider's
                    # "Unknown" country never permanently hides a real
                    # country another provider supplied for the same
                    # circuit.
                    countries[key] = resolve_country(event.circuit.country)

                championship_ids[key].add(championship_id)
                seasons[key].append(event.season)
                events[key].append(
                    CircuitEventEntry(
                        event_name=normalize_event_display(championship_id, event).grand_prix_name,
                        championship_id=championship_id,
                        championship_name=championship_name,
                        season=event.season,
                        event_uid=event.event_uid,
                    )
                )

        profiles: dict[str, CircuitProfile] = {}
        for key, name in names.items():
            sorted_ids = tuple(
                sorted(championship_ids[key], key=lambda cid: get_display_name(cid).casefold())
            )
            profiles[key] = CircuitProfile(
                circuit_key=key,
                name=name,
                country=countries[key],
                championship_ids=sorted_ids,
                championship_names=tuple(get_display_name(cid) for cid in sorted_ids),
                championship_count=len(sorted_ids),
                total_events=len(events[key]),
                first_season=min(seasons[key]),
                last_season=max(seasons[key]),
                events=tuple(
                    sorted(
                        events[key],
                        key=lambda e: (
                            e.season,
                            e.championship_name.casefold(),
                            e.event_name.casefold(),
                        ),
                    )
                ),
            )

        self._circuits = profiles

    def get_circuit(self, circuit_key: str) -> CircuitProfile | None:
        """The circuit profile for *circuit_key*, or ``None`` if unknown —
        e.g. a stale key from an index built before the last rebuild."""
        return self._circuits.get(circuit_key)

    def list_circuits(self) -> tuple[CircuitProfile, ...]:
        """Every indexed circuit, sorted alphabetically by name — the
        "base de données des circuits" itself, enumerable independently
        of any single lookup."""
        return tuple(sorted(self._circuits.values(), key=lambda c: c.name.casefold()))
