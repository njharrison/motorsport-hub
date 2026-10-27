"""SearchService — instant, offline search across championships, events,
and circuits already loaded in memory (Sprint 45).

No network calls, ever: the caller (``main_view.py``) builds an index once
from data it already fetched for other purposes — the registered
championship ids (``controller.list_championships``) and ``year_events``,
the exact same dict "Mon calendrier"'s season explorer already uses
(Sprint 40/41) — never a fresh provider scan per keystroke. Rebuilding the
index (e.g. when the user changes year on "Mon calendrier") is
main_view.py's job; searching against whatever index currently exists is
this module's only concern, and is O(index size), never O(fetch).

Reuses existing models end-to-end rather than inventing a second
normalization: ``display_names.get_display_name`` for championship names,
``event_display.normalize_event_display`` (Sprint 32, ADR-023) for event/
circuit display names — the exact same rules already used by
``ChampionshipCard``/the season explorer, so a circuit or event never
reads differently in search results than it does everywhere else in the
app. ``event_display.normalize_key`` (promoted here from this module at
Sprint 47 once ``gui/circuit_service.py`` needed the exact same "compact"
identity normalization for circuit deduplication) is the one place that
answers "are these two spellings the same real-world entity" — never
reimplemented a second time.
"""

from __future__ import annotations

from dataclasses import dataclass

from motorsport_calendar.gui.display_names import get_display_name
from motorsport_calendar.gui.event_display import normalize_event_display, normalize_key
from motorsport_calendar.models import Event


@dataclass(frozen=True)
class SearchResultItem:
    """One search result — pure display data, already formatted.

    ``subtitle`` is ``None`` when there is nothing more useful to show
    (e.g. a championship has no secondary line) — never an empty string.

    Sprint 55: carries identity, not rendered — so a click handler can
    resolve which existing view to open, without this module ever
    knowing that clicking is possible (same "identity carried through,
    never the domain object itself" convention as
    ``season_explorer.py::SeasonEventRow.championship_id``/``event_uid``,
    Sprint 42). Exactly one of the three is set, matching which tuple of
    ``SearchResults`` the item lives in:
      - championship result: ``championship_id`` only.
      - event result: ``championship_id`` (the *owning* championship)
        + ``event_uid`` — the same pair ``SeasonEventRow`` carries, so
        the same lookup in ``year_events`` resolves either one.
      - circuit result: ``circuit_key`` only — the same normalized key
        ``CircuitService``/``ChampionshipCardData``'s own circuit link
        already use (Sprint 47).
    """

    title: str
    subtitle: str | None = None
    championship_id: str | None = None
    event_uid: str | None = None
    circuit_key: str | None = None


@dataclass(frozen=True)
class SearchResults:
    """Results grouped by type (Sprint 45's own requirement), each tuple
    already sorted by relevance then alphabetically — the view never sorts
    or groups anything itself."""

    championships: tuple[SearchResultItem, ...] = ()
    events: tuple[SearchResultItem, ...] = ()
    circuits: tuple[SearchResultItem, ...] = ()

    @property
    def total_count(self) -> int:
        """Total number of results across all three categories."""
        return len(self.championships) + len(self.events) + len(self.circuits)

    @property
    def is_empty(self) -> bool:
        """True if no category returned any result."""
        return self.total_count == 0


@dataclass(frozen=True)
class _IndexedItem:
    """One indexed entity — the display item plus its precomputed
    normalized name, so a search never re-normalizes the whole dataset on
    every keystroke."""

    item: SearchResultItem
    normalized: str


@dataclass(frozen=True)
class _SearchIndex:
    championships: tuple[_IndexedItem, ...] = ()
    events: tuple[_IndexedItem, ...] = ()
    circuits: tuple[_IndexedItem, ...] = ()


def _relevance(query: str, normalized: str) -> int:
    """0 = exact match, 1 = starts with the query, 2 = contains it
    elsewhere — the primary sort key ("trié par pertinence")."""
    if normalized == query:
        return 0
    if normalized.startswith(query):
        return 1
    return 2


def _matches(query: str, indexed: tuple[_IndexedItem, ...]) -> tuple[SearchResultItem, ...]:
    scored = [
        (_relevance(query, entry.normalized), entry.item)
        for entry in indexed
        if query in entry.normalized
    ]
    scored.sort(key=lambda pair: (pair[0], pair[1].title.casefold()))
    return tuple(item for _, item in scored)


class SearchService:
    """Holds a rebuildable in-memory search index.

    Mirrors ``ConfigService``/``FavoritesService``'s own "service holds
    state, built fresh, exposes intent-revealing methods" pattern — here
    the state is the index. ``build_index`` is the only place that reads
    domain data; ``search`` never does.
    """

    def __init__(self) -> None:
        self._index = _SearchIndex()

    def build_index(self, championship_ids: list[str], year_events: dict[str, list[Event]]) -> None:
        """Rebuild the index from already-fetched data.

        Args:
            championship_ids: every registered championship id (
                ``controller.list_championships``) — always searchable,
                independent of whether ``year_events`` has resolved yet.
            year_events: every registered championship's events for the
                currently browsed year (``controller.get_calendar_year_events``,
                the same dict "Mon calendrier" already holds) — an empty
                dict is valid (before the background fetch resolves, or
                if it failed) and simply yields no event/circuit results.

        Safe to call as often as the underlying data changes; ``search()``
        is always O(index size), never O(re-fetch) — never touches
        providers/network itself.
        """
        championships = tuple(
            _IndexedItem(
                item=SearchResultItem(title=get_display_name(cid), championship_id=cid),
                normalized=normalize_key(get_display_name(cid)),
            )
            for cid in championship_ids
        )

        events: list[_IndexedItem] = []
        # Circuits are deduplicated by normalized name — the same circuit
        # hosts many events across championships/years; first occurrence
        # wins (country is expected to agree across occurrences).
        seen_circuits: dict[str, _IndexedItem] = {}
        for cid, championship_events in year_events.items():
            championship_name = get_display_name(cid)
            for event in championship_events:
                display = normalize_event_display(cid, event)
                events.append(
                    _IndexedItem(
                        item=SearchResultItem(
                            title=display.grand_prix_name,
                            subtitle=championship_name,
                            championship_id=cid,
                            event_uid=event.event_uid,
                        ),
                        normalized=normalize_key(display.grand_prix_name),
                    )
                )
                if display.circuit_name is not None and display.circuit_key is not None:
                    key = display.circuit_key
                    if key and key not in seen_circuits:
                        seen_circuits[key] = _IndexedItem(
                            item=SearchResultItem(
                                title=display.circuit_name,
                                subtitle=display.country,
                                circuit_key=key,
                            ),
                            normalized=key,
                        )

        self._index = _SearchIndex(
            championships=championships,
            events=tuple(events),
            circuits=tuple(seen_circuits.values()),
        )

    def search(self, query: str) -> SearchResults:
        """Pure, offline, instant — matches against the pre-built index
        only. A blank query returns no results at all (nothing typed,
        nothing to show — never "show everything", which an empty
        substring would otherwise match trivially).
        """
        normalized_query = normalize_key(query)
        if not normalized_query:
            return SearchResults()

        return SearchResults(
            championships=_matches(normalized_query, self._index.championships),
            events=_matches(normalized_query, self._index.events),
            circuits=_matches(normalized_query, self._index.circuits),
        )
