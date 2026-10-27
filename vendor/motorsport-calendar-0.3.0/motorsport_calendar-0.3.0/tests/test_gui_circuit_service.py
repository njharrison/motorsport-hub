"""Tests for gui.circuit_service — Sprint 47 circuit explorer.

No Flet dependency, no network: everything here builds an index directly
from ``Event``/``Circuit`` fixtures (the exact shape ``main_view.py``
already holds in ``year_events``) and asserts on the computed
``CircuitProfile`` objects.
"""

from __future__ import annotations

from motorsport_calendar.gui.circuit_service import CircuitService
from motorsport_calendar.models import (
    Championship,
    ChampionshipCategory,
    Circuit,
    Event,
)


def _event(
    *,
    championship_id: str = "formula1",
    name: str = "Belgian",
    season: int = 2026,
    circuit_name: str = "Spa-Francorchamps",
    circuit_city: str = "",
    country: str = "Belgium",
    event_uid: str | None = None,
) -> Event:
    championship = Championship(
        id=championship_id, name=championship_id, category=ChampionshipCategory.SINGLE_SEATER
    )
    circuit = Circuit(
        id=f"{circuit_name}-circuit",
        name=circuit_name,
        city=circuit_city or circuit_name,
        country=country,
        timezone="UTC",
    )
    return Event(
        championship=championship,
        season=season,
        round=1,
        name=name,
        circuit=circuit,
        sessions=(),
        event_uid=event_uid or f"{championship_id}-{name}-{season}@test",
    )


class TestEmptyIndex:
    def test_no_year_events_yields_no_circuits(self) -> None:
        service = CircuitService()
        service.build_index({})
        assert service.list_circuits() == ()

    def test_get_circuit_on_empty_index_returns_none(self) -> None:
        service = CircuitService()
        service.build_index({})
        assert service.get_circuit("spafrancorchamps") is None


class TestSingleCircuit:
    def test_basic_fields(self) -> None:
        service = CircuitService()
        event = _event()
        service.build_index({"formula1": [event]})
        profile = service.get_circuit("spafrancorchamps")
        assert profile is not None
        assert profile.name == "Spa-Francorchamps"
        assert profile.country == "🇧🇪 Belgique"
        assert profile.championship_count == 1
        assert profile.championship_ids == ("formula1",)
        assert profile.championship_names == ("Formula 1",)
        assert profile.total_events == 1
        assert profile.first_season == 2026
        assert profile.last_season == 2026

    def test_event_history_entry(self) -> None:
        service = CircuitService()
        event = _event(name="Belgian")
        service.build_index({"formula1": [event]})
        profile = service.get_circuit("spafrancorchamps")
        assert profile is not None
        assert len(profile.events) == 1
        entry = profile.events[0]
        assert entry.event_name == "Belgian Grand Prix"
        assert entry.championship_id == "formula1"
        assert entry.championship_name == "Formula 1"
        assert entry.season == 2026
        assert entry.event_uid == event.event_uid

    def test_country_hidden_when_unknown(self) -> None:
        service = CircuitService()
        event = _event(country="Unknown")
        service.build_index({"formula1": [event]})
        profile = service.get_circuit("spafrancorchamps")
        assert profile is not None
        assert profile.country is None

    def test_country_hidden_when_blank(self) -> None:
        service = CircuitService()
        event = _event(country="")
        service.build_index({"formula1": [event]})
        profile = service.get_circuit("spafrancorchamps")
        assert profile is not None
        assert profile.country is None


class TestCircuitDeduplication:
    """The same physical circuit, spelled differently across providers,
    must collapse into one entity — same guarantee already established for
    search (Sprint 45)."""

    def test_case_and_hyphen_insensitive(self) -> None:
        service = CircuitService()
        event1 = _event(
            championship_id="formula1", circuit_name="Spa-Francorchamps", event_uid="e1@test"
        )
        event2 = _event(
            championship_id="formula2", circuit_name="spa francorchamps", event_uid="e2@test"
        )
        service.build_index({"formula1": [event1], "formula2": [event2]})
        assert len(service.list_circuits()) == 1

    def test_merges_championships_across_providers(self) -> None:
        service = CircuitService()
        event1 = _event(
            championship_id="formula1", circuit_name="Spa-Francorchamps", event_uid="e1@test"
        )
        event2 = _event(
            championship_id="gtwc-europe", circuit_name="Spa-Francorchamps", event_uid="e2@test"
        )
        service.build_index({"formula1": [event1], "gtwc-europe": [event2]})
        profile = service.get_circuit("spafrancorchamps")
        assert profile is not None
        assert profile.championship_count == 2
        assert set(profile.championship_ids) == {"formula1", "gtwc-europe"}
        assert profile.total_events == 2

    def test_first_occurrence_name_wins(self) -> None:
        service = CircuitService()
        event1 = _event(
            championship_id="formula1", circuit_name="Spa-Francorchamps", event_uid="e1@test"
        )
        event2 = _event(
            championship_id="formula2", circuit_name="SPA FRANCORCHAMPS", event_uid="e2@test"
        )
        service.build_index({"formula1": [event1], "formula2": [event2]})
        profile = service.get_circuit("spafrancorchamps")
        assert profile is not None
        assert profile.name == "Spa-Francorchamps"

    def test_championship_names_sorted_alphabetically(self) -> None:
        service = CircuitService()
        event1 = _event(
            championship_id="wec", circuit_name="Spa-Francorchamps", event_uid="e1@test"
        )
        event2 = _event(
            championship_id="formula1", circuit_name="Spa-Francorchamps", event_uid="e2@test"
        )
        service.build_index({"wec": [event1], "formula1": [event2]})
        profile = service.get_circuit("spafrancorchamps")
        assert profile is not None
        assert profile.championship_names == ("FIA WEC", "Formula 1")

    def test_best_available_country_across_providers(self) -> None:
        """One provider's "Unknown" must never permanently hide a real
        country another provider supplied for the same circuit."""
        service = CircuitService()
        event_unknown = _event(
            championship_id="formula2",
            circuit_name="Spa-Francorchamps",
            country="Unknown",
            event_uid="e1@test",
        )
        event_known = _event(
            championship_id="formula1",
            circuit_name="Spa-Francorchamps",
            country="Belgium",
            event_uid="e2@test",
        )
        service.build_index({"formula2": [event_unknown], "formula1": [event_known]})
        profile = service.get_circuit("spafrancorchamps")
        assert profile is not None
        assert profile.country == "🇧🇪 Belgique"


class TestSeasonRange:
    def test_first_and_last_season_across_events(self) -> None:
        service = CircuitService()
        events = [
            _event(season=2024, event_uid="e2024@test"),
            _event(season=2026, event_uid="e2026@test"),
            _event(season=2025, event_uid="e2025@test"),
        ]
        service.build_index({"formula1": events})
        profile = service.get_circuit("spafrancorchamps")
        assert profile is not None
        assert profile.first_season == 2024
        assert profile.last_season == 2026


class TestEventHistorySorting:
    def test_sorted_by_season_then_championship_then_event_name(self) -> None:
        service = CircuitService()
        events_f1 = [
            _event(championship_id="formula1", season=2026, name="Belgian", event_uid="a@test"),
            _event(championship_id="formula1", season=2024, name="Dutch", event_uid="b@test"),
        ]
        events_wec = [
            _event(championship_id="wec", season=2025, name="Belgian", event_uid="c@test"),
        ]
        service.build_index({"formula1": events_f1, "wec": events_wec})
        profile = service.get_circuit("spafrancorchamps")
        assert profile is not None
        assert [e.season for e in profile.events] == [2024, 2025, 2026]


class TestListCircuits:
    def test_sorted_alphabetically_by_name(self) -> None:
        service = CircuitService()
        events = {
            "formula1": [
                _event(circuit_name="Zandvoort", event_uid="z@test"),
                _event(circuit_name="Austin", event_uid="a@test"),
                _event(circuit_name="Monza", event_uid="m@test"),
            ]
        }
        service.build_index(events)
        names = [c.name for c in service.list_circuits()]
        assert names == ["Austin", "Monza", "Zandvoort"]


class TestIndexRebuild:
    def test_rebuilding_replaces_the_previous_index(self) -> None:
        service = CircuitService()
        service.build_index({"formula1": [_event(circuit_name="Spa-Francorchamps")]})
        assert service.get_circuit("spafrancorchamps") is not None

        service.build_index({"formula1": [_event(circuit_name="Monza", event_uid="m@test")]})
        assert service.get_circuit("spafrancorchamps") is None
        assert service.get_circuit("monza") is not None
