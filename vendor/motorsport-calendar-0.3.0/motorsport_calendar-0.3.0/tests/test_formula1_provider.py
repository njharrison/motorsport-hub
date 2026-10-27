"""Tests for Formula1Provider, Formula1Source, and all source stubs."""

import pytest

from motorsport_calendar.models import ChampionshipCategory, Event
from motorsport_calendar.providers.formula1.provider import Formula1Provider
from motorsport_calendar.providers.formula1.source import Formula1Source
from motorsport_calendar.providers.formula1.sources.cached import CachedFormula1Source
from motorsport_calendar.providers.formula1.sources.ergast import ErgastSource
from motorsport_calendar.providers.formula1.sources.official import OfficialFormula1Source
from motorsport_calendar.providers.formula1.sources.openf1 import OpenF1Source

# ---------------------------------------------------------------------------
# Test double — a minimal in-memory source used across multiple tests
# ---------------------------------------------------------------------------


class FakeSource(Formula1Source):
    """Controllable Formula1Source for unit testing."""

    def __init__(self, events: list[Event] | None = None) -> None:
        self._events = events or []
        self.last_year_requested: int | None = None

    async def get_season(self, year: int) -> list[Event]:
        self.last_year_requested = year
        return self._events


# ---------------------------------------------------------------------------
# Formula1Source (abstract)
# ---------------------------------------------------------------------------


class TestFormula1SourceABC:
    def test_cannot_be_instantiated_directly(self) -> None:
        with pytest.raises(TypeError):
            Formula1Source()  # type: ignore[abstract]

    def test_concrete_subclass_can_be_instantiated(self) -> None:
        source = FakeSource()
        assert isinstance(source, Formula1Source)


# ---------------------------------------------------------------------------
# Formula1Provider — identity
# ---------------------------------------------------------------------------


class TestFormula1ProviderIdentity:
    def test_name_is_formula1(self) -> None:
        assert Formula1Provider(FakeSource()).name == "formula1"

    def test_supported_championships_contains_formula1(self) -> None:
        assert "formula1" in Formula1Provider(FakeSource()).supported_championships

    def test_accepts_any_formula1source_implementation(self) -> None:
        for source in (FakeSource(), CachedFormula1Source(FakeSource())):
            provider = Formula1Provider(source)
            assert provider.name == "formula1"


# ---------------------------------------------------------------------------
# Formula1Provider — fetch_events delegation
# ---------------------------------------------------------------------------


class TestFetchEvents:
    async def test_returns_events_from_source(self, australian_gp: Event) -> None:
        source = FakeSource([australian_gp])
        events = await Formula1Provider(source).fetch_events("formula1", 2025)
        assert events == [australian_gp]

    async def test_returns_empty_list_when_source_is_empty(self) -> None:
        events = await Formula1Provider(FakeSource()).fetch_events("formula1", 2025)
        assert events == []

    async def test_passes_year_to_source(self) -> None:
        source = FakeSource()
        await Formula1Provider(source).fetch_events("formula1", 2023)
        assert source.last_year_requested == 2023

    async def test_does_not_mutate_source_output(self, australian_gp: Event) -> None:
        source = FakeSource([australian_gp])
        events = await Formula1Provider(source).fetch_events("formula1", 2025)
        assert events is source._events


# ---------------------------------------------------------------------------
# Formula1Provider — fetch_championship
# ---------------------------------------------------------------------------


class TestFetchChampionship:
    async def test_returns_f1_championship(self) -> None:
        championship = await Formula1Provider(FakeSource()).fetch_championship("formula1", 2025)
        assert championship.id == "formula1-2025"
        assert championship.name == "Formula 1 World Championship"
        assert championship.category == ChampionshipCategory.SINGLE_SEATER

    async def test_id_contains_year(self) -> None:
        championship = await Formula1Provider(FakeSource()).fetch_championship("formula1", 2019)
        assert "2019" in championship.id

    async def test_different_years_produce_different_ids(self) -> None:
        provider = Formula1Provider(FakeSource())
        c2024 = await provider.fetch_championship("formula1", 2024)
        c2025 = await provider.fetch_championship("formula1", 2025)
        assert c2024.id != c2025.id


# ---------------------------------------------------------------------------
# Source stubs — still pending implementation
# ---------------------------------------------------------------------------


class TestSourceStubs:
    async def test_official_source_raises_not_implemented(self) -> None:
        with pytest.raises(NotImplementedError):
            await OfficialFormula1Source().get_season(2025)

    def test_ergast_source_is_jolpica_alias(self) -> None:
        # ErgastSource is now an alias for JolpicaSource (Ergast was shut down end-2024).
        # Its behaviour is covered in test_jolpica_source.py.
        from motorsport_calendar.providers.formula1.sources.jolpica import JolpicaSource

        assert ErgastSource is JolpicaSource

    def test_openf1_source_is_implemented(self) -> None:
        # OpenF1Source no longer raises NotImplementedError — it is a real implementation.
        # Its behaviour is covered in test_openf1_source.py.
        source = OpenF1Source()
        assert isinstance(source, OpenF1Source)

    async def test_cached_source_raises_not_implemented(self) -> None:
        with pytest.raises(NotImplementedError):
            await CachedFormula1Source(FakeSource()).get_season(2025)


# ---------------------------------------------------------------------------
# CachedFormula1Source — wrapping behaviour
# ---------------------------------------------------------------------------


class TestCachedFormula1Source:
    def test_stores_inner_source(self) -> None:
        inner = FakeSource()
        cached = CachedFormula1Source(inner)
        assert cached._source is inner

    def test_accepts_any_formula1source_as_inner(self) -> None:
        for inner in (FakeSource(), OfficialFormula1Source(), ErgastSource()):
            cached = CachedFormula1Source(inner)
            assert isinstance(cached._source, Formula1Source)
