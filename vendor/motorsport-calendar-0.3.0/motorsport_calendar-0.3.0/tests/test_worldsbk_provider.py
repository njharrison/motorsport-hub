"""Tests pour WorldSbkProvider, WorldSbkSource et OfficialWorldSbkSource."""

from datetime import UTC, datetime

from pydantic import ValidationError
import pytest

from motorsport_calendar.models import (
    Championship,
    ChampionshipCategory,
    Circuit,
    Event,
    Session,
    SessionType,
)
from motorsport_calendar.providers.worldsbk import WorldSbkProvider, WorldSbkSource
from motorsport_calendar.providers.worldsbk.sources import OfficialWorldSbkSource

TZ = UTC

# ---------------------------------------------------------------------------
# Test double — source en mémoire contrôlable
# ---------------------------------------------------------------------------


class FakeWorldSbkSource(WorldSbkSource):
    """WorldSbkSource minimal pour les tests unitaires."""

    def __init__(self, events: list[Event] | None = None) -> None:
        self._events = events or []
        self.last_year_requested: int | None = None

    async def get_season(self, year: int) -> list[Event]:
        self.last_year_requested = year
        return self._events


# ---------------------------------------------------------------------------
# Fixtures — événement WorldSBK réaliste
# ---------------------------------------------------------------------------


@pytest.fixture
def worldsbk_championship() -> Championship:
    return Championship(
        id="worldsbk-2026",
        name="FIM Superbike World Championship",
        category=ChampionshipCategory.MOTORBIKE,
    )


@pytest.fixture
def phillip_island_circuit() -> Circuit:
    return Circuit(
        id="worldsbk-phillip-island",
        name="Phillip Island Grand Prix Circuit",
        city="Phillip Island",
        country="Australia",
        timezone="Australia/Melbourne",
    )


@pytest.fixture
def worldsbk_sessions() -> tuple[Session, ...]:
    return (
        Session(
            type=SessionType.FREE_PRACTICE,
            start_datetime=datetime(2026, 2, 20, 1, 0, tzinfo=TZ),
            end_datetime=datetime(2026, 2, 20, 1, 25, tzinfo=TZ),
            title="Free Practice",
        ),
        Session(
            type=SessionType.QUALIFYING,
            start_datetime=datetime(2026, 2, 21, 2, 0, tzinfo=TZ),
            end_datetime=datetime(2026, 2, 21, 2, 30, tzinfo=TZ),
            title="Superpole",
        ),
        Session(
            type=SessionType.RACE,
            start_datetime=datetime(2026, 2, 22, 4, 0, tzinfo=TZ),
            end_datetime=datetime(2026, 2, 22, 4, 35, tzinfo=TZ),
            title="Race 1",
        ),
    )


@pytest.fixture
def phillip_island_worldsbk_event(
    worldsbk_championship: Championship,
    phillip_island_circuit: Circuit,
    worldsbk_sessions: tuple[Session, ...],
) -> Event:
    return Event(
        championship=worldsbk_championship,
        season=2026,
        round=1,
        name="Phillip Island Round",
        circuit=phillip_island_circuit,
        sessions=worldsbk_sessions,
        event_uid="worldsbk-2026-01-phillip-island@motorsport-calendar",
    )


# ---------------------------------------------------------------------------
# WorldSbkSource (abstract)
# ---------------------------------------------------------------------------


class TestWorldSbkSourceABC:
    def test_cannot_be_instantiated_directly(self) -> None:
        with pytest.raises(TypeError):
            WorldSbkSource()  # type: ignore[abstract]

    def test_concrete_subclass_can_be_instantiated(self) -> None:
        source = FakeWorldSbkSource()
        assert isinstance(source, WorldSbkSource)


# ---------------------------------------------------------------------------
# WorldSbkProvider — identité
# ---------------------------------------------------------------------------


class TestWorldSbkProviderIdentity:
    def test_name_is_worldsbk(self) -> None:
        assert WorldSbkProvider(FakeWorldSbkSource()).name == "worldsbk"

    def test_supported_championships_contains_worldsbk(self) -> None:
        assert "worldsbk" in WorldSbkProvider(FakeWorldSbkSource()).supported_championships

    def test_accepts_any_worldsbk_source(self) -> None:
        for source in (FakeWorldSbkSource(), OfficialWorldSbkSource()):
            provider = WorldSbkProvider(source)
            assert provider.name == "worldsbk"


# ---------------------------------------------------------------------------
# WorldSbkProvider — fetch_events
# ---------------------------------------------------------------------------


class TestFetchEvents:
    async def test_returns_events_from_source(self, phillip_island_worldsbk_event: Event) -> None:
        source = FakeWorldSbkSource([phillip_island_worldsbk_event])
        events = await WorldSbkProvider(source).fetch_events("worldsbk", 2026)
        assert events == [phillip_island_worldsbk_event]

    async def test_returns_empty_list_when_source_is_empty(self) -> None:
        events = await WorldSbkProvider(FakeWorldSbkSource()).fetch_events("worldsbk", 2026)
        assert events == []

    async def test_passes_year_to_source(self) -> None:
        source = FakeWorldSbkSource()
        await WorldSbkProvider(source).fetch_events("worldsbk", 2026)
        assert source.last_year_requested == 2026

    async def test_does_not_mutate_source_output(
        self, phillip_island_worldsbk_event: Event
    ) -> None:
        source = FakeWorldSbkSource([phillip_island_worldsbk_event])
        events = await WorldSbkProvider(source).fetch_events("worldsbk", 2026)
        assert events is source._events


# ---------------------------------------------------------------------------
# WorldSbkProvider — fetch_championship
# ---------------------------------------------------------------------------


class TestFetchChampionship:
    async def test_returns_worldsbk_championship(self) -> None:
        champ = await WorldSbkProvider(FakeWorldSbkSource()).fetch_championship("worldsbk", 2026)
        assert champ.id == "worldsbk-2026"
        assert champ.name == "FIM Superbike World Championship"
        assert champ.category == ChampionshipCategory.MOTORBIKE

    async def test_id_contains_year(self) -> None:
        champ = await WorldSbkProvider(FakeWorldSbkSource()).fetch_championship("worldsbk", 2024)
        assert "2024" in champ.id

    async def test_different_years_produce_different_ids(self) -> None:
        provider = WorldSbkProvider(FakeWorldSbkSource())
        c2025 = await provider.fetch_championship("worldsbk", 2025)
        c2026 = await provider.fetch_championship("worldsbk", 2026)
        assert c2025.id != c2026.id

    async def test_category_is_motorbike(self) -> None:
        champ = await WorldSbkProvider(FakeWorldSbkSource()).fetch_championship("worldsbk", 2026)
        assert champ.category == ChampionshipCategory.MOTORBIKE


# ---------------------------------------------------------------------------
# SessionType — types WorldSBK supportés
# ---------------------------------------------------------------------------


class TestWorldSbkSessionTypes:
    def test_free_practice_is_valid_session_type(self) -> None:
        assert SessionType.FREE_PRACTICE == "FREE_PRACTICE"

    def test_qualifying_is_valid_session_type(self) -> None:
        assert SessionType.QUALIFYING == "QUALIFYING"

    def test_race_is_valid_session_type(self) -> None:
        assert SessionType.RACE == "RACE"

    def test_worldsbk_event_contains_expected_session_types(
        self, worldsbk_sessions: tuple[Session, ...]
    ) -> None:
        types = {s.type for s in worldsbk_sessions}
        assert types == {
            SessionType.FREE_PRACTICE,
            SessionType.QUALIFYING,
            SessionType.RACE,
        }


# ---------------------------------------------------------------------------
# OfficialWorldSbkSource — stub
# ---------------------------------------------------------------------------


class TestOfficialWorldSbkSource:
    async def test_raises_not_implemented(self) -> None:
        with pytest.raises(NotImplementedError):
            await OfficialWorldSbkSource().get_season(2026)

    def test_is_a_worldsbk_source(self) -> None:
        assert isinstance(OfficialWorldSbkSource(), WorldSbkSource)


# ---------------------------------------------------------------------------
# Modèles — interopérabilité WorldSBK / F1
# ---------------------------------------------------------------------------


class TestModelInteroperability:
    def test_worldsbk_event_uses_standard_circuit_model(
        self, phillip_island_worldsbk_event: Event
    ) -> None:
        assert isinstance(phillip_island_worldsbk_event.circuit, Circuit)

    def test_worldsbk_event_uses_standard_championship_model(
        self, phillip_island_worldsbk_event: Event
    ) -> None:
        assert isinstance(phillip_island_worldsbk_event.championship, Championship)

    def test_worldsbk_and_f1_events_share_the_same_event_class(
        self, phillip_island_worldsbk_event: Event, australian_gp: Event
    ) -> None:
        assert type(phillip_island_worldsbk_event) is type(australian_gp)

    def test_worldsbk_event_is_frozen(self, phillip_island_worldsbk_event: Event) -> None:
        with pytest.raises(ValidationError):
            phillip_island_worldsbk_event.name = "modified"
