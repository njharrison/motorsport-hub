"""Event metadata normalization — Sprint 32.

Turns a raw domain ``Event`` into display-ready metadata for a
ChampionshipCard: which Grand Prix name to show, which circuit line (if
any), which country line (if any). This is the "dedicated logic" the
component itself must never contain — ``championship_card.py`` only
renders whatever it is given; every decision about *what* to show or hide
happens here.

Root cause investigation (why F1 looks better than F2/F3/F1 Academy)
----------------------------------------------------------------------
Confirmed by inspecting real provider output for the same weekend:

    formula1 | event.name='Belgian Grand Prix' | circuit.name='Spa-Francorchamps'
             | circuit.city='Spa-Francorchamps' | circuit.country='Belgium'
    formula2 | event.name='Belgian'             | circuit.name='Belgian'
             | circuit.city='Spa-Francorchamps' | circuit.country='Unknown'
    formula3 | event.name='Australian'          | circuit.name='Australian'
             | circuit.city='Melbourne'         | circuit.country='Australia'

Two independent causes, not one:

1. **A genuine, external API/dataset difference** (not a bug we can fix
   without touching providers). F1 (Jolpica/Ergast) returns a rich,
   dedicated field per race: a full ``raceName`` ("Belgian Grand Prix"), a
   real ``circuitName`` ("Spa-Francorchamps"), and a real country. F2/F3/F1
   Academy all come from the ``sportstimes/f1`` open dataset
   (f1calendar.com), which is far more minimal: each entry only has a short
   round descriptor (``name``: "Belgian", "Australian" — no "Grand Prix"
   suffix, no separate circuit-name field at all) and a ``location`` field
   that is closer to a venue/circuit name than an actual city (mapped to
   ``Circuit.city``). There is nothing richer to parse out of that dataset.

2. **A parsing/mapping choice in our own code**, in
   ``providers/support_series/f1calendar_base.py::_build_circuit`` —
   ``Circuit.name`` is set to the *same* short round descriptor as
   ``Event.name``, which is why the two end up identical ("Belgian" /
   "Belgian"). The dataset's ``location`` field (mapped to ``Circuit.city``)
   is actually a better circuit-name candidate and is already sitting
   there, just not used for that purpose. This is fixable — in the
   provider, which this sprint does not touch — not a domain-model
   limitation (``Circuit``/``Event`` have plenty of room for the right
   values; the F2/F3/F1 Academy provider code just doesn't have a good
   value to put in ``Circuit.name`` beyond what the dataset gives it).

   A secondary, separate gap: the static ``_CIRCUIT_DATA`` country lookup
   tables for F2/F3/F1 Academy are incomplete (many slugs are simply
   missing), which is why ``Circuit.country`` so often falls back to the
   literal sentinel ``"Unknown"`` for those series but rarely for F1. F3's
   table happens to cover more circuits than F2's, which is why F3 shows a
   real country ("Australia") for some events that F2 shows "Unknown" for
   — coverage varies per support-series module, not by design.

Given the constraint not to touch providers this sprint, this module
compensates entirely in the presentation layer: it never trusts
``Circuit.name`` blindly, falls back to ``Circuit.city`` when it looks like
a duplicate of the event name, and hides a line outright rather than ever
showing "Unknown", an empty line, or two identical lines.
"""

from __future__ import annotations

from dataclasses import dataclass
import unicodedata

from motorsport_calendar.gui.strings import STRINGS
from motorsport_calendar.models import Circuit, Event, Session, SessionType


def normalize_key(text: str) -> str:
    """Casefold + strip accents + keep only alphanumeric characters.

    A "compact" identity key so separator/case/accent differences never
    prevent two spellings of the same real-world entity from matching —
    "Le Mans"/"lemans" and "spa francorchamps"/"Spa-Francorchamps" must all
    collapse to the same key. Introduced for search matching (Sprint 45,
    ``gui/search_service.py``), promoted here once circuit identity
    (Sprint 47, ``gui/circuit_service.py``) needed the exact same
    normalization to deduplicate the same physical circuit across
    providers with inconsistent spelling — same "mutualize on the second
    real use" principle applied throughout this module (see
    ``session_type_label``).
    """
    decomposed = unicodedata.normalize("NFKD", text)
    without_accents = "".join(c for c in decomposed if not unicodedata.combining(c))
    return "".join(c for c in without_accents.casefold() if c.isalnum())


# ---------------------------------------------------------------------------
# Championships whose raw event name is a bare round descriptor ("Belgian")
# rather than a complete name ("Belgian Grand Prix") — see module docstring,
# cause #1. WEC (and any future non-GP series) already use complete names
# ("24 Hours of Le Mans") and must never get "Grand Prix" appended.
# ---------------------------------------------------------------------------

_GP_SUFFIX_CHAMPIONSHIPS = frozenset({"formula1", "formula2", "formula3", "f1-academy"})
_GP_SUFFIX = "Grand Prix"

# Circuit.country (as stored by providers, English) -> (flag emoji, French name).
# Not exhaustive — unmapped-but-known countries fall back to their raw stored
# name; the literal "Unknown" sentinel (and any blank value) hides the line
# entirely instead of ever being displayed (see _resolve_country).
_COUNTRY_LABELS: dict[str, tuple[str, str]] = {
    "Japan": ("🇯🇵", "Japon"),
    "Australia": ("🇦🇺", "Australie"),
    "Bahrain": ("🇧🇭", "Bahreïn"),
    "Saudi Arabia": ("🇸🇦", "Arabie saoudite"),
    "Azerbaijan": ("🇦🇿", "Azerbaïdjan"),
    "USA": ("🇺🇸", "États-Unis"),
    "United States": ("🇺🇸", "États-Unis"),
    "Spain": ("🇪🇸", "Espagne"),
    "Monaco": ("🇲🇨", "Monaco"),
    "Canada": ("🇨🇦", "Canada"),
    "Austria": ("🇦🇹", "Autriche"),
    "UK": ("🇬🇧", "Royaume-Uni"),
    "United Kingdom": ("🇬🇧", "Royaume-Uni"),
    "Hungary": ("🇭🇺", "Hongrie"),
    "Belgium": ("🇧🇪", "Belgique"),
    "Netherlands": ("🇳🇱", "Pays-Bas"),
    "Italy": ("🇮🇹", "Italie"),
    "Singapore": ("🇸🇬", "Singapour"),
    "Mexico": ("🇲🇽", "Mexique"),
    "Brazil": ("🇧🇷", "Brésil"),
    "UAE": ("🇦🇪", "Émirats arabes unis"),
    "United Arab Emirates": ("🇦🇪", "Émirats arabes unis"),
    "Qatar": ("🇶🇦", "Qatar"),
    "China": ("🇨🇳", "Chine"),
    "France": ("🇫🇷", "France"),
    "Germany": ("🇩🇪", "Allemagne"),
    "Portugal": ("🇵🇹", "Portugal"),
    "Russia": ("🇷🇺", "Russie"),
    "South Africa": ("🇿🇦", "Afrique du Sud"),
    "India": ("🇮🇳", "Inde"),
    "Malaysia": ("🇲🇾", "Malaisie"),
    "Korea": ("🇰🇷", "Corée du Sud"),
    "South Korea": ("🇰🇷", "Corée du Sud"),
    "Turkey": ("🇹🇷", "Turquie"),
    "Sweden": ("🇸🇪", "Suède"),
    "Finland": ("🇫🇮", "Finlande"),
    "Indonesia": ("🇮🇩", "Indonésie"),
}

# Values a provider uses to mean "I don't know the country" — never shown as-is.
_COUNTRY_UNKNOWN_SENTINELS = frozenset({"unknown", ""})

# SessionType -> French label. Sprint 42: promoted from upcoming_weekend.py's
# own private mapping once a second consumer (gui/event_details.py) needed
# the exact same session-type vocabulary — same "mutualize on the second
# real use" principle already applied to providers (Sprint 35) and
# controller fetch pipelines (Sprints 39-40).
_SESSION_TYPE_LABELS: dict[SessionType, str] = {
    SessionType.FP1: "Essais Libres 1",
    SessionType.FP2: "Essais Libres 2",
    SessionType.FP3: "Essais Libres 3",
    SessionType.FREE_PRACTICE: "Essais Libres",
    SessionType.QUALIFYING: "Qualifications",
    SessionType.SPRINT_QUALIFYING: "Qualifications Sprint",
    SessionType.SPRINT: "Sprint",
    SessionType.RACE: "Course",
    SessionType.TEST: "Essais",
    SessionType.HYPERPOLE: "Hyperpole",
}


def session_type_label(session: Session) -> str:
    """French label for *session*'s type — falls back to the session's own
    ``title`` for any type not in the mapping (defensive; every current
    ``SessionType`` is mapped)."""
    return _SESSION_TYPE_LABELS.get(session.type, session.title)


@dataclass(frozen=True)
class EventDisplayData:
    """Normalized, display-ready metadata for one event's ChampionshipCard.

    ``circuit_name``/``country`` are ``None`` when that line should be
    hidden entirely — never an empty string, never the literal "Unknown".
    ``grand_prix_name`` is always a non-empty string.

    ``circuit_key`` (Sprint 47) is the circuit's stable identity —
    ``normalize_key(circuit_name)`` — or ``None`` in lockstep with
    ``circuit_name``: when the circuit line is hidden for this event
    (redundant with the headline), there is no visible text to attach a
    click to, so nothing is clickable either. Used by
    ``gui/event_details.py``/``gui/circuit_service.py`` to open the
    "fiche Circuit" from a clicked circuit name — never interpreted here.
    """

    grand_prix_name: str
    circuit_name: str | None
    country: str | None
    circuit_key: str | None


def country_label(country: str) -> str:
    """ "🇯🇵 Japon"-style label. Falls back to the raw stored name when unmapped."""
    flag, name = _COUNTRY_LABELS.get(country, ("", country))
    return f"{flag} {name}".strip()


def _clean(value: str | None) -> str:
    return (value or "").strip()


def _first_nonempty(*values: str | None) -> str | None:
    for value in values:
        cleaned = _clean(value)
        if cleaned:
            return cleaned
    return None


def _display_grand_prix_name(championship_id: str, raw_name: str, circuit: Circuit) -> str:
    """Rule 4: decide what to call the event when the raw name is short,
    complete, or entirely absent."""
    if raw_name:
        if championship_id not in _GP_SUFFIX_CHAMPIONSHIPS:
            return raw_name  # WEC-style names are already complete.
        if _GP_SUFFIX.casefold() in raw_name.casefold():
            return raw_name  # Already complete — never double-suffix.
        return f"{raw_name} {_GP_SUFFIX}"

    # No event name at all: fall back to whatever circuit info exists,
    # rather than ever showing a blank headline.
    fallback = _first_nonempty(circuit.name, circuit.city)
    return fallback if fallback is not None else STRINGS.event_name_fallback


def _resolve_circuit_name(circuit: Circuit, raw_name: str, grand_prix_name: str) -> str | None:
    """Rules 1 & 2: never repeat the headline, never show a blank/duplicate
    circuit line. Tries ``circuit.name`` first, then ``circuit.city`` —
    the latter is often the better value for series whose provider reuses
    the round's short name for both (see module docstring)."""
    redundant = {raw_name.casefold(), grand_prix_name.casefold()}
    for candidate in (circuit.name, circuit.city):
        cleaned = _clean(candidate)
        if cleaned and cleaned.casefold() not in redundant:
            return cleaned
    return None


def resolve_country(raw_country: str) -> str | None:
    """Rule 3: the literal "Unknown" sentinel (or a blank value) hides the
    country line — it is never displayed as-is.

    Public since Sprint 47: ``gui/circuit_service.py`` reuses this exact
    same "never show Unknown" rule for a circuit's own country field —
    the resolution logic has nothing to do with any one event's headline
    (unlike ``_resolve_circuit_name``), so it applies identically to a
    circuit-as-entity.
    """
    cleaned = _clean(raw_country)
    if cleaned.casefold() in _COUNTRY_UNKNOWN_SENTINELS:
        return None
    return country_label(cleaned)


def circuit_display_name(circuit: Circuit) -> str:
    """The circuit's own name — first non-empty of ``circuit.name``/
    ``circuit.city`` — independent of any single event's headline.

    Unlike ``_resolve_circuit_name`` (which hides a value that would be
    *redundant* with one specific event's card), this always answers "what
    is this circuit called" — used to identify/name a circuit as an entity
    in its own right (Sprint 47, ``gui/circuit_service.py``), not to
    decide whether a display line should render under one event's
    headline.
    """
    fallback = _first_nonempty(circuit.name, circuit.city)
    return fallback if fallback is not None else STRINGS.circuit_name_fallback


def normalize_event_display(championship_id: str, event: Event) -> EventDisplayData:
    """Turn *event* into normalized, display-ready ChampionshipCard metadata.

    Args:
        championship_id: the registry id (e.g. "formula1") — decides
            whether the "Grand Prix" suffix rule applies (see module
            docstring, cause #1).
        event: the raw fetched event. Never mutated; nothing here reaches
            into providers or business logic — purely a data transform.
    """
    raw_name = _clean(event.name)
    grand_prix_name = _display_grand_prix_name(championship_id, raw_name, event.circuit)
    circuit_name = _resolve_circuit_name(event.circuit, raw_name, grand_prix_name)
    country = resolve_country(event.circuit.country)
    circuit_key = normalize_key(circuit_name) if circuit_name is not None else None
    return EventDisplayData(
        grand_prix_name=grand_prix_name,
        circuit_name=circuit_name,
        country=country,
        circuit_key=circuit_key,
    )
