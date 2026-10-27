"""Tests pour WecProvider, WecSource et OfficialWecSource."""

from datetime import UTC, datetime, timedelta

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
from motorsport_calendar.providers.wec import WecProvider, WecSource
from motorsport_calendar.providers.wec.sources import OfficialWecSource

TZ = UTC

# ---------------------------------------------------------------------------
# Test double — source en mémoire contrôlable
# ---------------------------------------------------------------------------


class FakeWecSource(WecSource):
    """WecSource minimal pour les tests unitaires."""

    def __init__(self, events: list[Event] | None = None) -> None:
        self._events = events or []
        self.last_year_requested: int | None = None

    async def get_season(self, year: int) -> list[Event]:
        self.last_year_requested = year
        return self._events


# ---------------------------------------------------------------------------
# Fixtures — événement WEC réaliste
# ---------------------------------------------------------------------------


@pytest.fixture
def wec_championship() -> Championship:
    return Championship(
        id="wec-2026",
        name="FIA World Endurance Championship",
        category=ChampionshipCategory.ENDURANCE,
    )


@pytest.fixture
def spa_circuit() -> Circuit:
    return Circuit(
        id="wec-spa",
        name="Spa-Francorchamps",
        city="Stavelot",
        country="Belgium",
        timezone="Europe/Brussels",
    )


@pytest.fixture
def wec_sessions() -> tuple[Session, ...]:
    return (
        Session(
            type=SessionType.FREE_PRACTICE,
            start_datetime=datetime(2026, 5, 7, 10, 0, tzinfo=TZ),
            end_datetime=datetime(2026, 5, 7, 13, 0, tzinfo=TZ),
            title="Free Practice",
        ),
        Session(
            type=SessionType.QUALIFYING,
            start_datetime=datetime(2026, 5, 8, 10, 0, tzinfo=TZ),
            end_datetime=datetime(2026, 5, 8, 11, 0, tzinfo=TZ),
            title="Qualifying",
        ),
        Session(
            type=SessionType.HYPERPOLE,
            start_datetime=datetime(2026, 5, 8, 14, 0, tzinfo=TZ),
            end_datetime=datetime(2026, 5, 8, 14, 30, tzinfo=TZ),
            title="Hyperpole",
        ),
        Session(
            type=SessionType.RACE,
            start_datetime=datetime(2026, 5, 9, 14, 0, tzinfo=TZ),
            end_datetime=datetime(2026, 5, 10, 14, 0, tzinfo=TZ),
            title="6 Hours of Spa-Francorchamps",
        ),
    )


@pytest.fixture
def spa_wec_event(
    wec_championship: Championship,
    spa_circuit: Circuit,
    wec_sessions: tuple[Session, ...],
) -> Event:
    return Event(
        championship=wec_championship,
        season=2026,
        round=1,
        name="6 Hours of Spa-Francorchamps",
        circuit=spa_circuit,
        sessions=wec_sessions,
        event_uid="wec-2026-01-spa@motorsport-calendar",
    )


# ---------------------------------------------------------------------------
# WecSource (abstract)
# ---------------------------------------------------------------------------


class TestWecSourceABC:
    def test_cannot_be_instantiated_directly(self) -> None:
        with pytest.raises(TypeError):
            WecSource()  # type: ignore[abstract]

    def test_concrete_subclass_can_be_instantiated(self) -> None:
        source = FakeWecSource()
        assert isinstance(source, WecSource)


# ---------------------------------------------------------------------------
# WecProvider — identité
# ---------------------------------------------------------------------------


class TestWecProviderIdentity:
    def test_name_is_wec(self) -> None:
        assert WecProvider(FakeWecSource()).name == "wec"

    def test_supported_championships_contains_wec(self) -> None:
        assert "wec" in WecProvider(FakeWecSource()).supported_championships

    def test_accepts_any_wec_source(self) -> None:
        for source in (FakeWecSource(), OfficialWecSource()):
            provider = WecProvider(source)
            assert provider.name == "wec"


# ---------------------------------------------------------------------------
# WecProvider — fetch_events
# ---------------------------------------------------------------------------


class TestFetchEvents:
    async def test_returns_events_from_source(self, spa_wec_event: Event) -> None:
        source = FakeWecSource([spa_wec_event])
        events = await WecProvider(source).fetch_events("wec", 2026)
        assert events == [spa_wec_event]

    async def test_returns_empty_list_when_source_is_empty(self) -> None:
        events = await WecProvider(FakeWecSource()).fetch_events("wec", 2026)
        assert events == []

    async def test_passes_year_to_source(self) -> None:
        source = FakeWecSource()
        await WecProvider(source).fetch_events("wec", 2026)
        assert source.last_year_requested == 2026

    async def test_does_not_mutate_source_output(self, spa_wec_event: Event) -> None:
        source = FakeWecSource([spa_wec_event])
        events = await WecProvider(source).fetch_events("wec", 2026)
        assert events is source._events


# ---------------------------------------------------------------------------
# WecProvider — fetch_championship
# ---------------------------------------------------------------------------


class TestFetchChampionship:
    async def test_returns_wec_championship(self) -> None:
        champ = await WecProvider(FakeWecSource()).fetch_championship("wec", 2026)
        assert champ.id == "wec-2026"
        assert champ.name == "FIA World Endurance Championship"
        assert champ.category == ChampionshipCategory.ENDURANCE

    async def test_id_contains_year(self) -> None:
        champ = await WecProvider(FakeWecSource()).fetch_championship("wec", 2024)
        assert "2024" in champ.id

    async def test_different_years_produce_different_ids(self) -> None:
        provider = WecProvider(FakeWecSource())
        c2025 = await provider.fetch_championship("wec", 2025)
        c2026 = await provider.fetch_championship("wec", 2026)
        assert c2025.id != c2026.id

    async def test_category_is_endurance(self) -> None:
        champ = await WecProvider(FakeWecSource()).fetch_championship("wec", 2026)
        assert champ.category == ChampionshipCategory.ENDURANCE


# ---------------------------------------------------------------------------
# SessionType — types WEC supportés
# ---------------------------------------------------------------------------


class TestWecSessionTypes:
    def test_free_practice_is_valid_session_type(self) -> None:
        assert SessionType.FREE_PRACTICE == "FREE_PRACTICE"

    def test_qualifying_is_valid_session_type(self) -> None:
        assert SessionType.QUALIFYING == "QUALIFYING"

    def test_hyperpole_is_valid_session_type(self) -> None:
        assert SessionType.HYPERPOLE == "HYPERPOLE"

    def test_race_is_valid_session_type(self) -> None:
        assert SessionType.RACE == "RACE"

    def test_wec_event_contains_all_four_session_types(
        self, wec_sessions: tuple[Session, ...]
    ) -> None:
        types = {s.type for s in wec_sessions}
        assert types == {
            SessionType.FREE_PRACTICE,
            SessionType.QUALIFYING,
            SessionType.HYPERPOLE,
            SessionType.RACE,
        }


# ---------------------------------------------------------------------------
# OfficialWecSource — real implementation (Sprint 48), backed by
# fiawec.com's own JSON-LD (same ACO CMS as ELMS/MLMC, Sprint 35).
# ---------------------------------------------------------------------------


class TestOfficialWecSourceIdentity:
    def test_is_a_wec_source(self) -> None:
        assert isinstance(OfficialWecSource(), WecSource)

    def test_is_an_aco_sports_event_source(self) -> None:
        from motorsport_calendar.providers.aco_series.sports_event_base import (
            AcoSportsEventSource,
        )

        assert isinstance(OfficialWecSource(), AcoSportsEventSource)

    def test_series_key(self) -> None:
        assert OfficialWecSource()._series_key == "wec"

    def test_base_url(self) -> None:
        assert OfficialWecSource()._base_url == "https://www.fiawec.com"

    def test_event_name_prefix(self) -> None:
        assert OfficialWecSource()._event_name_prefix == "WEC"


class TestOfficialWecSourceRaceDuration:
    """_race_session_end() override — the base class's endDate-trust logic
    does not work for WEC (verified empirically, Sprint 48: fiawec.com's
    event-level endDate is always midnight of the last announced day,
    unrelated to the race's actual finish time). Duration is instead
    parsed from the race's own name."""

    def _source(self) -> OfficialWecSource:
        return OfficialWecSource()

    def test_parses_hours_from_name(self) -> None:
        start = datetime(2026, 4, 19, 13, 0, tzinfo=TZ)
        end = self._source()._race_session_end(start, None, "WEC 6 Hours of Imola 2026")
        assert end == start + timedelta(hours=6)

    def test_parses_24_hours_le_mans(self) -> None:
        start = datetime(2026, 6, 13, 16, 0, tzinfo=TZ)
        end = self._source()._race_session_end(start, None, "WEC 24 Hours of Le Mans 2026")
        assert end == start + timedelta(hours=24)

    def test_lone_star_le_mans_is_six_hours(self) -> None:
        """No parseable "X Hours" in the name — hardcoded from its
        publicly documented duration (see docs/DATA_SOURCES.md)."""
        start = datetime(2026, 9, 6, 13, 0, tzinfo=TZ)
        end = self._source()._race_session_end(start, None, "WEC Lone Star Le Mans 2026")
        assert end == start + timedelta(hours=6)

    def test_qatar_1812km_is_ten_hours(self) -> None:
        start = datetime(2026, 10, 24, 13, 0, tzinfo=TZ)
        end = self._source()._race_session_end(start, None, "WEC Qatar 1812km 2026")
        assert end == start + timedelta(hours=10)

    def test_unrecognised_name_falls_back_to_six_hours(self) -> None:
        start = datetime(2026, 1, 1, 13, 0, tzinfo=TZ)
        end = self._source()._race_session_end(start, None, "WEC Some New Race 2027")
        assert end == start + timedelta(hours=6)

    def test_ignores_event_end_entirely(self) -> None:
        """Even a "plausible"-looking event_end must never be trusted —
        this is the exact bug caught live for the 24 Hours of Le Mans
        (endDate ~8h after start, silently wrong for a 24h race)."""
        start = datetime(2026, 6, 13, 16, 0, tzinfo=TZ)
        misleading_event_end = start + timedelta(hours=8)
        end = self._source()._race_session_end(
            start, misleading_event_end, "WEC 24 Hours of Le Mans 2026"
        )
        assert end == start + timedelta(hours=24)


class TestOfficialWecSourceCircuitCountry:
    """_build_circuit() override — country resolved from the JSON-LD
    location.address field ("{city}, {ISO alpha-3 code}"), not a static
    per-venue table (see wec/circuit_data.py)."""

    def _build(self, location: dict) -> Circuit:
        source = OfficialWecSource()
        return source._build_circuit({"location": location})

    def test_resolves_country_from_address_code(self) -> None:
        circuit = self._build({"name": "Imola", "address": "Imola, ITA"})
        assert circuit.country == "Italy"
        assert circuit.timezone == "Europe/Rome"

    def test_different_address_code_than_known_venue(self) -> None:
        circuit = self._build({"name": "Interlagos", "address": "Sao Paulo, BRA"})
        assert circuit.country == "Brazil"

    def test_falls_back_to_static_table_when_address_missing(self) -> None:
        circuit = self._build({"name": "Imola"})
        assert circuit.country == "Italy"  # WEC_CIRCUIT_DATA fallback
        assert circuit.timezone == "Europe/Rome"

    def test_falls_back_to_static_table_when_code_unmapped(self) -> None:
        circuit = self._build({"name": "Imola", "address": "Imola, XYZ"})
        assert circuit.country == "Italy"  # WEC_CIRCUIT_DATA fallback, not "XYZ"

    def test_unknown_venue_and_unmapped_code(self) -> None:
        circuit = self._build({"name": "Somewhere New", "address": "Somewhere, XYZ"})
        assert circuit.country == "Unknown"
        assert circuit.timezone == "UTC"

    def test_circuit_id_is_series_prefixed(self) -> None:
        circuit = self._build({"name": "Imola", "address": "Imola, ITA"})
        assert circuit.id == "wec-imola"


class TestOfficialWecSourceSeasonFiltering:
    """_race_url_belongs_to_season() override — fiawec.com's
    /en/season/{year} page lists next year's races too (confirmed
    empirically, Sprint 48), distinguished only by URL suffix."""

    def test_accepts_matching_year_suffix(self) -> None:
        source = OfficialWecSource()
        url = "https://www.fiawec.com/en/race/6-hours-of-imola-2026"
        assert source._race_url_belongs_to_season(url, 2026) is True

    def test_rejects_different_year_suffix(self) -> None:
        source = OfficialWecSource()
        url = "https://www.fiawec.com/en/race/6-hours-of-imola-2027"
        assert source._race_url_belongs_to_season(url, 2026) is False


class TestOfficialWecSourceRealFixtures:
    """End-to-end parsing against real captured fiawec.com JSON-LD
    (tests/fixtures/real/wec_*.html — verbatim, never hand-crafted, see
    that directory's convention already established by ELMS/MLMC)."""

    def _load(self, name: str) -> str:
        from pathlib import Path

        return (Path(__file__).parent / "fixtures" / "real" / name).read_text()

    def _build_imola_event(self) -> Event:
        source = OfficialWecSource()
        data = source._extract_json_ld(self._load("wec_race_imola.html"))
        championship = source._make_championship(2026)
        return source._build_event(championship, data, round_number=1, year=2026)

    def _build_le_mans_event(self) -> Event:
        source = OfficialWecSource()
        data = source._extract_json_ld(self._load("wec_race_le_mans.html"))
        championship = source._make_championship(2026)
        return source._build_event(championship, data, round_number=3, year=2026)

    def test_imola_event_name(self) -> None:
        assert self._build_imola_event().name == "6 Hours of Imola"

    def test_imola_circuit(self) -> None:
        event = self._build_imola_event()
        assert event.circuit.name == "Imola"
        assert event.circuit.country == "Italy"
        assert event.circuit.timezone == "Europe/Rome"

    def test_imola_six_sessions_no_duplicates(self) -> None:
        event = self._build_imola_event()
        types = [s.type for s in event.sessions]
        assert len(types) == len(set(types))
        assert set(types) == {
            SessionType.FP1,
            SessionType.FP2,
            SessionType.FP3,
            SessionType.QUALIFYING,
            SessionType.HYPERPOLE,
            SessionType.RACE,
        }

    def test_imola_hyperpole_merges_both_class_slots(self) -> None:
        """Fixture reports the LMGT3 slot at 14:50 Europe/Rome (+02:00);
        _parse_datetime normalises to UTC (MC-002 P0-1), so 12:50 here."""
        event = self._build_imola_event()
        hyperpole = next(s for s in event.sessions if s.type == SessionType.HYPERPOLE)
        assert hyperpole.start_datetime.hour == 12
        assert hyperpole.start_datetime.minute == 50

    def test_imola_race_is_six_hours(self) -> None:
        event = self._build_imola_event()
        race = next(s for s in event.sessions if s.type == SessionType.RACE)
        assert race.end_datetime - race.start_datetime == timedelta(hours=6)

    def test_imola_uids_unique(self) -> None:
        event = self._build_imola_event()
        uids = [f"{event.event_uid}-{s.type.value}" for s in event.sessions]
        assert len(uids) == len(set(uids))

    def test_le_mans_has_eight_distinct_session_types(self) -> None:
        """FP1/FP2/FP3/FREE_PRACTICE(=FP4)/QUALIFYING/HYPERPOLE/TEST(=Warm-up)/RACE."""
        event = self._build_le_mans_event()
        types = {s.type for s in event.sessions}
        assert types == {
            SessionType.FP1,
            SessionType.FP2,
            SessionType.FP3,
            SessionType.FREE_PRACTICE,
            SessionType.QUALIFYING,
            SessionType.HYPERPOLE,
            SessionType.TEST,
            SessionType.RACE,
        }

    def test_le_mans_race_is_24_hours(self) -> None:
        """The critical regression this sprint's investigation caught:
        fiawec.com's own endDate would silently give ~8 hours here."""
        event = self._build_le_mans_event()
        race = next(s for s in event.sessions if s.type == SessionType.RACE)
        assert race.end_datetime - race.start_datetime == timedelta(hours=24)

    def test_le_mans_free_practice_4_distinct_from_warm_up(self) -> None:
        event = self._build_le_mans_event()
        fp4 = next(s for s in event.sessions if s.type == SessionType.FREE_PRACTICE)
        warm_up = next(s for s in event.sessions if s.type == SessionType.TEST)
        assert fp4.start_datetime != warm_up.start_datetime
        assert (warm_up.start_datetime - fp4.start_datetime) > timedelta(hours=30)

    def test_le_mans_qualifying_merges_both_days_and_classes(self) -> None:
        """Le Mans runs Qualifying across 2 classes on day 1 only (unlike
        Hyperpole, which repeats on day 2) — still exercises the same
        multi-slot merge logic."""
        event = self._build_le_mans_event()
        qualifying = next(s for s in event.sessions if s.type == SessionType.QUALIFYING)
        assert qualifying.end_datetime > qualifying.start_datetime

    def test_le_mans_uids_unique(self) -> None:
        event = self._build_le_mans_event()
        uids = [f"{event.event_uid}-{s.type.value}" for s in event.sessions]
        assert len(uids) == len(set(uids))


class TestOfficialWecSourceGetSeasonIntegration:
    """get_season() end-to-end with mocked fetch_html — real season
    snippet (prologue + 2026/2027 mixed years) + real race fixtures."""

    def _load(self, name: str) -> str:
        from pathlib import Path

        return (Path(__file__).parent / "fixtures" / "real" / name).read_text()

    async def test_excludes_prologue_and_other_years(self, monkeypatch) -> None:
        season_html = self._load("wec_season_snippet.html")
        imola_html = self._load("wec_race_imola.html")

        async def fake_fetch_html(self: OfficialWecSource, url: str) -> str:
            if "season" in url:
                return season_html
            return imola_html  # every race page resolves to Imola's JSON-LD

        monkeypatch.setattr(OfficialWecSource, "fetch_html", fake_fetch_html)
        source = OfficialWecSource(cache=None)
        events = await source.get_season(2026)
        # wec_season_snippet.html lists exactly 2 real 2026 rounds
        # (Imola, Spa) once the prologue and 2027 rounds are filtered out.
        assert len(events) == 2
        assert all(e.season == 2026 for e in events)


# ---------------------------------------------------------------------------
# Modèles — interopérabilité WEC / F1
# ---------------------------------------------------------------------------


class TestModelInteroperability:
    def test_wec_event_uses_standard_circuit_model(self, spa_wec_event: Event) -> None:
        assert isinstance(spa_wec_event.circuit, Circuit)

    def test_wec_event_uses_standard_championship_model(self, spa_wec_event: Event) -> None:
        assert isinstance(spa_wec_event.championship, Championship)

    def test_wec_and_f1_events_share_the_same_event_class(
        self, spa_wec_event: Event, australian_gp: Event
    ) -> None:
        assert type(spa_wec_event) is type(australian_gp)

    def test_wec_event_is_frozen(self, spa_wec_event: Event) -> None:
        with pytest.raises(ValidationError):
            spa_wec_event.name = "modified"
