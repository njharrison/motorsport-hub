"""Tests pour ImsaProvider, ImsaSource et OfficialImsaSource."""

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
from motorsport_calendar.providers.imsa import ImsaProvider, ImsaSource
from motorsport_calendar.providers.imsa.sources import OfficialImsaSource

TZ = UTC

# ---------------------------------------------------------------------------
# Test double — source en mémoire contrôlable
# ---------------------------------------------------------------------------


class FakeImsaSource(ImsaSource):
    """ImsaSource minimal pour les tests unitaires."""

    def __init__(self, events: list[Event] | None = None) -> None:
        self._events = events or []
        self.last_year_requested: int | None = None

    async def get_season(self, year: int) -> list[Event]:
        self.last_year_requested = year
        return self._events


# ---------------------------------------------------------------------------
# Fixtures — événement IMSA réaliste
# ---------------------------------------------------------------------------


@pytest.fixture
def imsa_championship() -> Championship:
    return Championship(
        id="imsa-2026",
        name="IMSA WeatherTech SportsCar Championship",
        category=ChampionshipCategory.ENDURANCE,
    )


@pytest.fixture
def daytona_circuit() -> Circuit:
    return Circuit(
        id="imsa-daytona",
        name="Daytona International Speedway",
        city="Daytona Beach",
        country="USA",
        timezone="America/New_York",
    )


@pytest.fixture
def imsa_sessions() -> tuple[Session, ...]:
    return (
        Session(
            type=SessionType.FREE_PRACTICE,
            start_datetime=datetime(2026, 1, 22, 15, 0, tzinfo=TZ),
            end_datetime=datetime(2026, 1, 22, 17, 0, tzinfo=TZ),
            title="Practice 1",
        ),
        Session(
            type=SessionType.QUALIFYING,
            start_datetime=datetime(2026, 1, 23, 18, 0, tzinfo=TZ),
            end_datetime=datetime(2026, 1, 23, 19, 0, tzinfo=TZ),
            title="Qualifying",
        ),
        Session(
            type=SessionType.RACE,
            start_datetime=datetime(2026, 1, 24, 18, 40, tzinfo=TZ),
            end_datetime=datetime(2026, 1, 25, 18, 40, tzinfo=TZ),
            title="Rolex 24 at Daytona",
        ),
    )


@pytest.fixture
def daytona_imsa_event(
    imsa_championship: Championship,
    daytona_circuit: Circuit,
    imsa_sessions: tuple[Session, ...],
) -> Event:
    return Event(
        championship=imsa_championship,
        season=2026,
        round=1,
        name="Rolex 24 at Daytona",
        circuit=daytona_circuit,
        sessions=imsa_sessions,
        event_uid="imsa-2026-01-daytona@motorsport-calendar",
    )


# ---------------------------------------------------------------------------
# ImsaSource (abstract)
# ---------------------------------------------------------------------------


class TestImsaSourceABC:
    def test_cannot_be_instantiated_directly(self) -> None:
        with pytest.raises(TypeError):
            ImsaSource()  # type: ignore[abstract]

    def test_concrete_subclass_can_be_instantiated(self) -> None:
        source = FakeImsaSource()
        assert isinstance(source, ImsaSource)


# ---------------------------------------------------------------------------
# ImsaProvider — identité
# ---------------------------------------------------------------------------


class TestImsaProviderIdentity:
    def test_name_is_imsa(self) -> None:
        assert ImsaProvider(FakeImsaSource()).name == "imsa"

    def test_supported_championships_contains_imsa(self) -> None:
        assert "imsa" in ImsaProvider(FakeImsaSource()).supported_championships

    def test_accepts_any_imsa_source(self) -> None:
        for source in (FakeImsaSource(), OfficialImsaSource()):
            provider = ImsaProvider(source)
            assert provider.name == "imsa"


# ---------------------------------------------------------------------------
# ImsaProvider — fetch_events
# ---------------------------------------------------------------------------


class TestFetchEvents:
    async def test_returns_events_from_source(self, daytona_imsa_event: Event) -> None:
        source = FakeImsaSource([daytona_imsa_event])
        events = await ImsaProvider(source).fetch_events("imsa", 2026)
        assert events == [daytona_imsa_event]

    async def test_returns_empty_list_when_source_is_empty(self) -> None:
        events = await ImsaProvider(FakeImsaSource()).fetch_events("imsa", 2026)
        assert events == []

    async def test_passes_year_to_source(self) -> None:
        source = FakeImsaSource()
        await ImsaProvider(source).fetch_events("imsa", 2026)
        assert source.last_year_requested == 2026

    async def test_does_not_mutate_source_output(self, daytona_imsa_event: Event) -> None:
        source = FakeImsaSource([daytona_imsa_event])
        events = await ImsaProvider(source).fetch_events("imsa", 2026)
        assert events is source._events


# ---------------------------------------------------------------------------
# ImsaProvider — fetch_championship
# ---------------------------------------------------------------------------


class TestFetchChampionship:
    async def test_returns_imsa_championship(self) -> None:
        champ = await ImsaProvider(FakeImsaSource()).fetch_championship("imsa", 2026)
        assert champ.id == "imsa-2026"
        assert champ.name == "IMSA WeatherTech SportsCar Championship"
        assert champ.category == ChampionshipCategory.ENDURANCE

    async def test_id_contains_year(self) -> None:
        champ = await ImsaProvider(FakeImsaSource()).fetch_championship("imsa", 2024)
        assert "2024" in champ.id

    async def test_different_years_produce_different_ids(self) -> None:
        provider = ImsaProvider(FakeImsaSource())
        c2025 = await provider.fetch_championship("imsa", 2025)
        c2026 = await provider.fetch_championship("imsa", 2026)
        assert c2025.id != c2026.id

    async def test_category_is_endurance(self) -> None:
        champ = await ImsaProvider(FakeImsaSource()).fetch_championship("imsa", 2026)
        assert champ.category == ChampionshipCategory.ENDURANCE


# ---------------------------------------------------------------------------
# SessionType — types IMSA supportés
# ---------------------------------------------------------------------------


class TestImsaSessionTypes:
    def test_free_practice_is_valid_session_type(self) -> None:
        assert SessionType.FREE_PRACTICE == "FREE_PRACTICE"

    def test_qualifying_is_valid_session_type(self) -> None:
        assert SessionType.QUALIFYING == "QUALIFYING"

    def test_race_is_valid_session_type(self) -> None:
        assert SessionType.RACE == "RACE"

    def test_imsa_event_contains_expected_session_types(
        self, imsa_sessions: tuple[Session, ...]
    ) -> None:
        types = {s.type for s in imsa_sessions}
        assert types == {
            SessionType.FREE_PRACTICE,
            SessionType.QUALIFYING,
            SessionType.RACE,
        }


# ---------------------------------------------------------------------------
# OfficialImsaSource — stub
# ---------------------------------------------------------------------------


class TestOfficialImsaSource:
    async def test_raises_not_implemented(self) -> None:
        with pytest.raises(NotImplementedError):
            await OfficialImsaSource().get_season(2026)

    def test_is_an_imsa_source(self) -> None:
        assert isinstance(OfficialImsaSource(), ImsaSource)


# ---------------------------------------------------------------------------
# Modèles — interopérabilité IMSA / F1
# ---------------------------------------------------------------------------


class TestModelInteroperability:
    def test_imsa_event_uses_standard_circuit_model(self, daytona_imsa_event: Event) -> None:
        assert isinstance(daytona_imsa_event.circuit, Circuit)

    def test_imsa_event_uses_standard_championship_model(self, daytona_imsa_event: Event) -> None:
        assert isinstance(daytona_imsa_event.championship, Championship)

    def test_imsa_and_f1_events_share_the_same_event_class(
        self, daytona_imsa_event: Event, australian_gp: Event
    ) -> None:
        assert type(daytona_imsa_event) is type(australian_gp)

    def test_imsa_event_is_frozen(self, daytona_imsa_event: Event) -> None:
        with pytest.raises(ValidationError):
            daytona_imsa_event.name = "modified"
