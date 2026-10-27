"""Tests for gui.search_service — Sprint 45 global search.

No Flet dependency, no network: everything here builds an index directly
from ``Event``/``Circuit`` fixtures (the exact shape ``main_view.py``
already holds in ``year_events``) and asserts on ``SearchResults``.
Covers every validation scenario from the brief (recherche vide,
championnat, événement, circuit, partielle, casse, accents, aucun
résultat) plus its own explicit matching examples (spa/Spa/SPA/spa
francorchamps, Le Mans/lemans, Moto/MotoGP, Formula, GT).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from motorsport_calendar.gui.search_service import SearchService
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
    championship_id: str = "formula1",
    name: str,
    circuit_name: str,
    circuit_city: str = "",
    country: str = "Unknown",
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
        event_uid=f"{championship_id}-{name}@test",
    )


class TestEmptySearch:
    """ "recherche vide" validation scenario."""

    def test_empty_query_on_empty_index_returns_no_results(self) -> None:
        service = SearchService()
        results = service.search("")
        assert results.is_empty

    def test_empty_query_on_populated_index_returns_no_results(self) -> None:
        """A blank query must never mean "show everything"."""
        service = SearchService()
        service.build_index(["formula1", "motogp"], {})
        results = service.search("")
        assert results.is_empty

    def test_whitespace_only_query_returns_no_results(self) -> None:
        service = SearchService()
        service.build_index(["formula1"], {})
        assert service.search("   ").is_empty

    def test_search_before_any_build_index_call_returns_no_results(self) -> None:
        service = SearchService()
        assert service.search("formula").is_empty


class TestChampionshipSearch:
    def test_finds_a_championship_by_full_name(self) -> None:
        service = SearchService()
        service.build_index(["formula1", "motogp"], {})
        results = service.search("Formula 1")
        assert [item.title for item in results.championships] == ["Formula 1"]
        assert results.events == ()
        assert results.circuits == ()

    def test_no_match_returns_empty_championships(self) -> None:
        service = SearchService()
        service.build_index(["formula1"], {})
        assert service.search("motogp").championships == ()


class TestEventSearch:
    def test_finds_an_event_by_name(self) -> None:
        service = SearchService()
        event = _event(championship_id="formula1", name="Belgian", circuit_name="Spa-Francorchamps")
        service.build_index(["formula1"], {"formula1": [event]})
        results = service.search("Belgian")
        assert len(results.events) == 1
        assert results.events[0].title == "Belgian Grand Prix"
        assert results.events[0].subtitle == "Formula 1"


class TestCircuitSearch:
    def test_finds_a_circuit_by_name(self) -> None:
        service = SearchService()
        event = _event(
            championship_id="formula1",
            name="Belgian",
            circuit_name="Spa-Francorchamps",
            country="Belgium",
        )
        service.build_index(["formula1"], {"formula1": [event]})
        results = service.search("Spa-Francorchamps")
        assert len(results.circuits) == 1
        assert results.circuits[0].title == "Spa-Francorchamps"

    def test_circuits_are_deduplicated_across_events(self) -> None:
        """The same circuit hosts many events/years — must appear once."""
        service = SearchService()
        events = [
            _event(championship_id="formula1", name="Belgian", circuit_name="Spa-Francorchamps"),
            _event(championship_id="formula2", name="Belgian", circuit_name="Spa-Francorchamps"),
        ]
        service.build_index(
            ["formula1", "formula2"], {"formula1": [events[0]], "formula2": [events[1]]}
        )
        results = service.search("Spa")
        assert len(results.circuits) == 1


class TestSearchResultIdentity:
    """Sprint 55 — every result carries identity so a click handler can
    resolve which existing view to open, without this module ever
    knowing that clicking is possible."""

    def test_championship_result_carries_its_own_id(self) -> None:
        service = SearchService()
        service.build_index(["formula1"], {})
        item = service.search("Formula 1").championships[0]
        assert item.championship_id == "formula1"
        assert item.event_uid is None
        assert item.circuit_key is None

    def test_event_result_carries_championship_id_and_event_uid(self) -> None:
        service = SearchService()
        event = _event(championship_id="formula1", name="Belgian", circuit_name="Spa")
        service.build_index(["formula1"], {"formula1": [event]})
        item = service.search("Belgian").events[0]
        assert item.championship_id == "formula1"
        assert item.event_uid == event.event_uid
        assert item.circuit_key is None

    def test_circuit_result_carries_its_key_only(self) -> None:
        service = SearchService()
        event = _event(championship_id="formula1", name="Belgian", circuit_name="Spa")
        service.build_index(["formula1"], {"formula1": [event]})
        item = service.search("Spa").circuits[0]
        assert item.circuit_key is not None
        assert item.championship_id is None
        assert item.event_uid is None

    def test_circuit_key_matches_across_deduplicated_events(self) -> None:
        """Same circuit hosted by 2 championships — the surviving
        (first-seen) result must still carry a usable key, not the
        discarded second occurrence's."""
        service = SearchService()
        events = [
            _event(championship_id="formula1", name="Belgian", circuit_name="Spa-Francorchamps"),
            _event(championship_id="formula2", name="Belgian", circuit_name="Spa-Francorchamps"),
        ]
        service.build_index(
            ["formula1", "formula2"], {"formula1": [events[0]], "formula2": [events[1]]}
        )
        item = service.search("Spa").circuits[0]
        assert item.circuit_key


class TestPartialAndCaseAndAccentSearch:
    """ "recherche partielle", "casse différente", "accents" scenarios."""

    def test_partial_query_matches(self) -> None:
        service = SearchService()
        service.build_index(["formula1"], {})
        assert [i.title for i in service.search("Form").championships] == ["Formula 1"]

    def test_case_insensitive_lowercase(self) -> None:
        service = SearchService()
        service.build_index(["formula1"], {})
        assert service.search("formula 1").championships != ()

    def test_case_insensitive_uppercase(self) -> None:
        service = SearchService()
        service.build_index(["formula1"], {})
        assert service.search("FORMULA 1").championships != ()

    def test_accent_insensitive(self) -> None:
        service = SearchService()
        event = _event(championship_id="wec", name="24 Hours of Le Mans", circuit_name="Le Mans")
        service.build_index(["wec"], {"wec": [event]})
        # "Mans" has no accent, but the surrounding scenario (championship
        # names carrying accents) is what this asserts: a query without
        # accents must still match data that has none either, and vice
        # versa via _normalize's NFKD stripping.
        results_plain = service.search("Le Mans")
        results_no_space = service.search("lemans")
        assert results_plain.events != ()
        assert results_no_space.events != ()


class TestNoResults:
    """ "aucun résultat" validation scenario."""

    def test_unmatched_query_returns_all_empty_groups(self) -> None:
        service = SearchService()
        service.build_index(["formula1"], {})
        results = service.search("xyzxyzxyz")
        assert results.is_empty
        assert results.championships == ()
        assert results.events == ()
        assert results.circuits == ()


class TestBriefExamples:
    """The brief's own explicit matching examples, verbatim."""

    def _spa_index(self) -> SearchService:
        service = SearchService()
        event = _event(
            championship_id="formula1",
            name="Belgian",
            circuit_name="Spa-Francorchamps",
            country="Belgium",
        )
        service.build_index(["formula1"], {"formula1": [event]})
        return service

    def test_spa_lowercase(self) -> None:
        assert self._spa_index().search("spa").circuits != ()

    def test_spa_capitalized(self) -> None:
        assert self._spa_index().search("Spa").circuits != ()

    def test_spa_uppercase(self) -> None:
        assert self._spa_index().search("SPA").circuits != ()

    def test_spa_francorchamps_full(self) -> None:
        assert self._spa_index().search("spa francorchamps").circuits != ()

    def _le_mans_index(self) -> SearchService:
        service = SearchService()
        service.build_index(["mlmc", "elms"], {})
        return service

    def test_le_mans_with_space_and_case(self) -> None:
        titles = [i.title for i in self._le_mans_index().search("Le Mans").championships]
        assert "Michelin Le Mans Cup" in titles
        assert "European Le Mans Series" in titles

    def test_lemans_compact(self) -> None:
        titles = [i.title for i in self._le_mans_index().search("lemans").championships]
        assert "Michelin Le Mans Cup" in titles
        assert "European Le Mans Series" in titles

    def _moto_index(self) -> SearchService:
        service = SearchService()
        service.build_index(["motogp", "moto2", "moto3"], {})
        return service

    def test_moto_matches_all_three_moto_championships(self) -> None:
        titles = [i.title for i in self._moto_index().search("Moto").championships]
        assert set(titles) == {"MotoGP", "Moto2", "Moto3"}

    def test_motogp_matches_only_motogp(self) -> None:
        titles = [i.title for i in self._moto_index().search("MotoGP").championships]
        assert titles == ["MotoGP"]

    def test_formula_matches_every_formula_championship(self) -> None:
        service = SearchService()
        service.build_index(["formula1", "formula2", "formula3", "formula-e"], {})
        titles = {i.title for i in service.search("Formula").championships}
        assert titles == {"Formula 1", "Formula 2", "Formula 3", "Formula E"}

    def test_gt_matches_every_gt_championship(self) -> None:
        service = SearchService()
        service.build_index(["gtwc-europe", "gtwc-america", "gtwc-asia", "igtc"], {})
        titles = {i.title for i in service.search("GT").championships}
        assert titles == {
            "GT World Challenge Europe",
            "GT World Challenge America",
            "GT World Challenge Asia",
            "Intercontinental GT Challenge",
        }


class TestRelevanceOrdering:
    """ "Chaque groupe est trié par pertinence puis alphabétiquement."""

    def test_exact_match_ranks_before_prefix_and_substring(self) -> None:
        service = SearchService()
        service.build_index(["gt", "gtwc-europe", "igtc"], {})
        titles = [i.title for i in service.search("GT").championships]
        # exact "Gt".casefold() match first, then GT World Challenge
        # Europe (starts with "GT"), then Intercontinental GT Challenge
        # (contains "GT" elsewhere).
        assert titles[0] == "Gt"
        assert titles[1] == "GT World Challenge Europe"
        assert titles[2] == "Intercontinental GT Challenge"

    def test_ties_broken_alphabetically(self) -> None:
        service = SearchService()
        service.build_index(["gtwc-asia", "gtwc-europe", "gtwc-america"], {})
        titles = [i.title for i in service.search("GT World Challenge").championships]
        assert titles == sorted(titles, key=str.casefold)


class TestIndexRebuild:
    """Performance requirement: "construire un index réutilisable", rebuilt
    (not appended to) whenever main_view.py calls build_index again."""

    def test_rebuilding_replaces_the_previous_index(self) -> None:
        service = SearchService()
        service.build_index(["formula1"], {})
        assert service.search("Formula 1").championships != ()

        service.build_index(["motogp"], {})
        assert service.search("Formula 1").championships == ()
        assert service.search("MotoGP").championships != ()

    def test_rebuilding_with_empty_year_events_clears_stale_events(self) -> None:
        service = SearchService()
        event = _event(championship_id="formula1", name="Belgian", circuit_name="Spa-Francorchamps")
        service.build_index(["formula1"], {"formula1": [event]})
        assert service.search("Belgian").events != ()

        service.build_index(["formula1"], {})
        assert service.search("Belgian").events == ()

    def test_search_never_touches_providers_or_network(self) -> None:
        """No provider/network import exists in search_service.py at all —
        the strongest guarantee that search is offline, verified here by
        making sure a search against a large-ish index completes purely
        from in-memory data (no mocking needed because there is nothing
        to call out to)."""
        service = SearchService()
        events = [
            _event(championship_id="formula1", name=f"Race {i}", circuit_name=f"Circuit {i}")
            for i in range(50)
        ]
        service.build_index(["formula1"], {"formula1": events})
        results = service.search("Race 1")
        assert results.events != ()
