"""Tests for gui.event_display — Sprint 32 metadata normalization.

Covers exactly what the sprint asked for: never "Unknown", never a blank
line, never a duplicate line, and a documented, consistent strategy for a
missing Grand Prix name. Includes the real F1/F2/F3 fixtures captured live
during the root-cause investigation (see the module docstring and
docs/JOURNAL.md for the full analysis).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from motorsport_calendar.gui.event_display import (
    EventDisplayData,
    circuit_display_name,
    country_label,
    normalize_event_display,
    normalize_key,
    resolve_country,
)
from motorsport_calendar.models import (
    Championship,
    ChampionshipCategory,
    Circuit,
    Event,
    Session,
    SessionType,
)


def _event(
    *,
    name: str,
    circuit_name: str,
    circuit_city: str,
    country: str,
) -> Event:
    championship = Championship(id="x-9999", name="x", category=ChampionshipCategory.SINGLE_SEATER)
    circuit = Circuit(id="c", name=circuit_name, city=circuit_city, country=country, timezone="UTC")
    session = Session(
        type=SessionType.RACE,
        start_datetime=datetime(2026, 7, 12, 13, 0, tzinfo=UTC),
        end_datetime=datetime(2026, 7, 12, 13, 0, tzinfo=UTC) + timedelta(hours=2),
        title="Race",
    )
    return Event(
        championship=championship,
        season=2026,
        round=1,
        name=name,
        circuit=circuit,
        sessions=(session,),
        event_uid="x-1@test",
    )


class TestRealF1Fixture:
    """Captured live from get_upcoming_weekend() during the Sprint 32
    investigation — F1's Jolpica source gives rich, distinct fields."""

    def test_all_three_lines_shown_unchanged(self) -> None:
        event = _event(
            name="Belgian Grand Prix",
            circuit_name="Spa-Francorchamps",
            circuit_city="Spa-Francorchamps",
            country="Belgium",
        )
        display = normalize_event_display("formula1", event)
        assert display == EventDisplayData(
            grand_prix_name="Belgian Grand Prix",
            circuit_name="Spa-Francorchamps",
            country="🇧🇪 Belgique",
            circuit_key="spafrancorchamps",
        )


class TestRealF2Bug:
    """Captured live: F2's provider reuses the bare round name for both
    Event.name and Circuit.name, and its country lookup table has no entry
    for "belgian" — the exact "Belgian / Belgian / Unknown" the sprint
    brief complained about."""

    def test_duplicate_becomes_one_clean_headline_plus_city_as_circuit(self) -> None:
        event = _event(
            name="Belgian",
            circuit_name="Belgian",
            circuit_city="Spa-Francorchamps",
            country="Unknown",
        )
        display = normalize_event_display("formula2", event)
        assert display.grand_prix_name == "Belgian Grand Prix"
        assert display.circuit_name == "Spa-Francorchamps"
        assert display.country is None


class TestRealF3PartialCoverage:
    """F3's country lookup table happens to cover this circuit, unlike
    F2's — demonstrating the coverage gap is per-module, not systemic."""

    def test_country_shown_when_the_lookup_table_has_it(self) -> None:
        event = _event(
            name="Australian",
            circuit_name="Australian",
            circuit_city="Melbourne",
            country="Australia",
        )
        display = normalize_event_display("formula3", event)
        assert display.grand_prix_name == "Australian Grand Prix"
        assert display.circuit_name == "Melbourne"
        assert display.country == "🇦🇺 Australie"


class TestNeverUnknown:
    def test_literal_unknown_sentinel_hides_the_country_line(self) -> None:
        event = _event(name="Race", circuit_name="Circuit", circuit_city="City", country="Unknown")
        assert normalize_event_display("formula1", event).country is None

    def test_unknown_is_case_insensitive(self) -> None:
        event = _event(name="Race", circuit_name="Circuit", circuit_city="City", country="UNKNOWN")
        assert normalize_event_display("formula1", event).country is None

    def test_blank_country_also_hides_the_line(self) -> None:
        event = _event(name="Race", circuit_name="Circuit", circuit_city="City", country="")
        assert normalize_event_display("formula1", event).country is None

    def test_known_country_still_renders_flag_and_french_name(self) -> None:
        event = _event(name="Race", circuit_name="Circuit", circuit_city="City", country="Japan")
        assert normalize_event_display("formula1", event).country == "🇯🇵 Japon"


class TestNeverADuplicateLine:
    def test_circuit_name_equal_to_raw_event_name_falls_back_to_city(self) -> None:
        event = _event(
            name="Dutch", circuit_name="Dutch", circuit_city="Zandvoort", country="Netherlands"
        )
        display = normalize_event_display("formula2", event)
        assert display.circuit_name == "Zandvoort"

    def test_circuit_name_and_city_both_duplicate_hides_the_line_entirely(self) -> None:
        event = _event(
            name="Dutch", circuit_name="Dutch", circuit_city="Dutch", country="Netherlands"
        )
        display = normalize_event_display("formula2", event)
        assert display.circuit_name is None

    def test_comparison_is_case_insensitive(self) -> None:
        event = _event(
            name="dutch", circuit_name="DUTCH", circuit_city="Zandvoort", country="Netherlands"
        )
        display = normalize_event_display("formula2", event)
        assert display.circuit_name == "Zandvoort"

    def test_distinct_circuit_name_is_kept(self) -> None:
        event = _event(
            name="Dutch Grand Prix",
            circuit_name="Zandvoort",
            circuit_city="Zandvoort",
            country="Netherlands",
        )
        display = normalize_event_display("formula1", event)
        assert display.circuit_name == "Zandvoort"

    def test_blank_circuit_name_and_city_hides_the_line(self) -> None:
        event = _event(name="Race", circuit_name="", circuit_city="", country="France")
        assert normalize_event_display("formula1", event).circuit_name is None


class TestGrandPrixNameStrategy:
    """Rule 4: what to call the event when the raw name is short, already
    complete, or entirely absent."""

    def test_short_name_gets_grand_prix_appended_for_gp_style_championships(self) -> None:
        for cid in ("formula1", "formula2", "formula3", "f1-academy"):
            event = _event(
                name="Qatar", circuit_name="Lusail", circuit_city="Lusail", country="Qatar"
            )
            assert normalize_event_display(cid, event).grand_prix_name == "Qatar Grand Prix"

    def test_already_complete_name_is_not_double_suffixed(self) -> None:
        event = _event(
            name="Monaco Grand Prix",
            circuit_name="Monte Carlo",
            circuit_city="Monte Carlo",
            country="Monaco",
        )
        display = normalize_event_display("formula1", event)
        assert display.grand_prix_name == "Monaco Grand Prix"

    def test_completeness_check_is_case_insensitive(self) -> None:
        event = _event(
            name="Monaco grand prix",
            circuit_name="Monte Carlo",
            circuit_city="Monte Carlo",
            country="Monaco",
        )
        display = normalize_event_display("formula1", event)
        assert display.grand_prix_name == "Monaco grand prix"

    def test_non_gp_style_championship_is_passed_through_unchanged(self) -> None:
        """WEC-style names ("24 Hours of Le Mans") must never get "Grand
        Prix" appended — they are already complete on their own terms."""
        event = _event(
            name="24 Hours of Le Mans",
            circuit_name="Circuit des 24 Heures",
            circuit_city="Le Mans",
            country="France",
        )
        display = normalize_event_display("wec", event)
        assert display.grand_prix_name == "24 Hours of Le Mans"

    def test_missing_name_falls_back_to_circuit_name(self) -> None:
        event = _event(
            name="", circuit_name="Silverstone", circuit_city="Silverstone", country="UK"
        )
        display = normalize_event_display("formula1", event)
        assert display.grand_prix_name == "Silverstone"
        assert display.circuit_name is None  # would just repeat the headline

    def test_missing_name_falls_back_to_circuit_city_when_name_is_blank(self) -> None:
        event = _event(name="", circuit_name="", circuit_city="Silverstone", country="UK")
        display = normalize_event_display("formula1", event)
        assert display.grand_prix_name == "Silverstone"

    def test_missing_name_and_missing_circuit_uses_the_generic_fallback(self) -> None:
        event = _event(name="", circuit_name="", circuit_city="", country="")
        display = normalize_event_display("formula1", event)
        assert display.grand_prix_name == "Événement"
        assert display.circuit_name is None
        assert display.country is None

    def test_blank_name_is_treated_the_same_as_missing(self) -> None:
        event = _event(
            name="   ", circuit_name="Silverstone", circuit_city="Silverstone", country="UK"
        )
        display = normalize_event_display("formula1", event)
        assert display.grand_prix_name == "Silverstone"


class TestCountryLabel:
    """country_label() itself — moved here from upcoming_weekend.py."""

    def test_known_country_gets_flag_and_french_name(self) -> None:
        assert country_label("Japan") == "🇯🇵 Japon"

    def test_unmapped_country_falls_back_to_the_raw_name(self) -> None:
        assert country_label("Atlantis") == "Atlantis"


class TestEventDisplayDataIsFrozen:
    def test_cannot_mutate_after_construction(self) -> None:
        import pytest

        data = EventDisplayData(
            grand_prix_name="x", circuit_name=None, country=None, circuit_key=None
        )
        with pytest.raises(AttributeError):
            data.grand_prix_name = "y"  # type: ignore[misc]


class TestNormalizeKey:
    """Promoted to public at Sprint 47 (moved from search_service.py's own
    private ``_normalize``) — the shared "compact identity key" used by
    both search matching (Sprint 45) and circuit deduplication
    (Sprint 47)."""

    def test_case_insensitive(self) -> None:
        assert normalize_key("Spa") == normalize_key("SPA") == normalize_key("spa")

    def test_accent_insensitive(self) -> None:
        assert normalize_key("Le Mans") == normalize_key("Le Mãns")

    def test_separator_insensitive(self) -> None:
        assert normalize_key("Spa-Francorchamps") == normalize_key("spa francorchamps")

    def test_different_names_produce_different_keys(self) -> None:
        assert normalize_key("Spa") != normalize_key("Spa-Francorchamps")


class TestResolveCountry:
    """Promoted to public at Sprint 47 (renamed from ``_resolve_country``)
    — same "never show Unknown" rule reused for circuit identity."""

    def test_known_country_resolves_to_its_label(self) -> None:
        assert resolve_country("Belgium") == "🇧🇪 Belgique"

    def test_unknown_sentinel_hides_the_line(self) -> None:
        assert resolve_country("Unknown") is None

    def test_blank_hides_the_line(self) -> None:
        assert resolve_country("") is None


class TestCircuitDisplayName:
    """New at Sprint 47 — a circuit's own name, independent of any single
    event's headline (unlike ``_resolve_circuit_name``, which hides a
    value that would be redundant with one specific card)."""

    def _circuit(self, *, name: str = "", city: str = "") -> Circuit:
        return Circuit(id="c", name=name, city=city, country="France", timezone="UTC")

    def test_prefers_circuit_name(self) -> None:
        circuit = self._circuit(name="Spa-Francorchamps", city="Spa")
        assert circuit_display_name(circuit) == "Spa-Francorchamps"

    def test_falls_back_to_city_when_name_is_blank(self) -> None:
        circuit = self._circuit(name="", city="Spa-Francorchamps")
        assert circuit_display_name(circuit) == "Spa-Francorchamps"

    def test_never_hides_a_value_for_being_redundant(self) -> None:
        """Unlike _resolve_circuit_name — this is the circuit's own name,
        not a decision about whether to show a line under a headline."""
        circuit = self._circuit(name="Belgian", city="Belgian")
        assert circuit_display_name(circuit) == "Belgian"

    def test_falls_back_to_a_generic_label_when_both_are_blank(self) -> None:
        circuit = self._circuit(name="", city="")
        assert circuit_display_name(circuit) == "Circuit inconnu"


class TestEventDisplayDataCircuitKey:
    """``circuit_key`` (Sprint 47) is in lockstep with ``circuit_name`` —
    ``None`` exactly when the circuit line itself is hidden."""

    def test_circuit_key_set_when_circuit_name_is_shown(self) -> None:
        event = _event(
            name="Belgian Grand Prix",
            circuit_name="Spa-Francorchamps",
            circuit_city="Spa-Francorchamps",
            country="Belgium",
        )
        display = normalize_event_display("formula1", event)
        assert display.circuit_name == "Spa-Francorchamps"
        assert display.circuit_key == "spafrancorchamps"

    def test_circuit_key_is_none_when_circuit_name_is_hidden(self) -> None:
        event = _event(
            name="Belgian",
            circuit_name="Belgian",
            circuit_city="Belgian",
            country="Belgium",
        )
        display = normalize_event_display("formula2", event)
        assert display.circuit_name is None
        assert display.circuit_key is None
