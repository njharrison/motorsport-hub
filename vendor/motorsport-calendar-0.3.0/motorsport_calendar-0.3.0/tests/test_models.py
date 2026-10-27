"""Tests for Pydantic models."""

from datetime import UTC, datetime

from pydantic import ValidationError
import pytest

from motorsport_calendar.models import (
    Championship,
    ChampionshipCategory,
    Circuit,
    Event,
    EventStatus,
    Session,
    SessionType,
)

TZ = UTC


# ---------------------------------------------------------------------------
# SessionType
# ---------------------------------------------------------------------------


class TestSessionType:
    def test_all_values_defined(self) -> None:
        values = {s.value for s in SessionType}
        assert values == {
            "FP1",
            "FP2",
            "FP3",
            "QUALIFYING",
            "SPRINT_QUALIFYING",
            "SPRINT",
            "RACE",
            "FREE_PRACTICE",
            "TEST",
            "HYPERPOLE",
        }

    def test_is_str(self) -> None:
        assert isinstance(SessionType.RACE, str)
        assert SessionType.RACE == "RACE"


# ---------------------------------------------------------------------------
# Championship
# ---------------------------------------------------------------------------


class TestChampionship:
    def test_creation(self, f1: Championship) -> None:
        assert f1.id == "f1"
        assert f1.name == "Formula 1 World Championship"
        assert f1.category == ChampionshipCategory.SINGLE_SEATER

    def test_all_categories_valid(self) -> None:
        for cat in ChampionshipCategory:
            c = Championship(id="x", name="X", category=cat)
            assert c.category == cat

    def test_invalid_category_raises(self) -> None:
        with pytest.raises(ValidationError):
            Championship(id="x", name="X", category="Drone Racing")  # type: ignore[arg-type]

    def test_immutable(self, f1: Championship) -> None:
        with pytest.raises(ValidationError):
            f1.name = "Changed"


# ---------------------------------------------------------------------------
# Circuit
# ---------------------------------------------------------------------------


class TestCircuit:
    def test_creation(self, albert_park: Circuit) -> None:
        assert albert_park.id == "albert-park"
        assert albert_park.city == "Melbourne"
        assert albert_park.country == "Australia"
        assert albert_park.timezone == "Australia/Melbourne"

    def test_all_fields_required(self) -> None:
        with pytest.raises(ValidationError):
            Circuit(id="x", name="X", city="Paris", country="France")  # type: ignore[call-arg]

    def test_immutable(self, albert_park: Circuit) -> None:
        with pytest.raises(ValidationError):
            albert_park.name = "Changed"


# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------


class TestSession:
    def test_creation(self, race_session: Session) -> None:
        assert race_session.type == SessionType.RACE
        assert race_session.title == "Australian Grand Prix — Race"
        assert race_session.description == "Round 1 of the 2025 season."

    def test_description_optional(self, qualifying_session: Session) -> None:
        assert qualifying_session.description is None

    def test_naive_start_datetime_raises(self) -> None:
        with pytest.raises(ValidationError, match="timezone-aware"):
            Session(
                type=SessionType.RACE,
                start_datetime=datetime(2025, 3, 16, 5, 0),  # naive
                end_datetime=datetime(2025, 3, 16, 7, 0, tzinfo=TZ),
                title="Race",
            )

    def test_naive_end_datetime_raises(self) -> None:
        with pytest.raises(ValidationError, match="timezone-aware"):
            Session(
                type=SessionType.RACE,
                start_datetime=datetime(2025, 3, 16, 5, 0, tzinfo=TZ),
                end_datetime=datetime(2025, 3, 16, 7, 0),  # naive
                title="Race",
            )

    def test_end_before_start_raises(self) -> None:
        with pytest.raises(ValidationError, match="strictly after"):
            Session(
                type=SessionType.QUALIFYING,
                start_datetime=datetime(2025, 3, 16, 8, 0, tzinfo=TZ),
                end_datetime=datetime(2025, 3, 16, 7, 0, tzinfo=TZ),
                title="Qualifying",
            )

    def test_end_equal_start_raises(self) -> None:
        with pytest.raises(ValidationError, match="strictly after"):
            Session(
                type=SessionType.FP1,
                start_datetime=datetime(2025, 3, 14, 10, 0, tzinfo=TZ),
                end_datetime=datetime(2025, 3, 14, 10, 0, tzinfo=TZ),
                title="FP1",
            )

    def test_invalid_session_type_raises(self) -> None:
        with pytest.raises(ValidationError):
            Session(
                type="UNKNOWN_TYPE",  # type: ignore[arg-type]
                start_datetime=datetime(2025, 3, 16, 5, 0, tzinfo=TZ),
                end_datetime=datetime(2025, 3, 16, 7, 0, tzinfo=TZ),
                title="Race",
            )

    def test_immutable(self, race_session: Session) -> None:
        with pytest.raises(ValidationError):
            race_session.title = "Changed"


# ---------------------------------------------------------------------------
# EventStatus
# ---------------------------------------------------------------------------


class TestEventStatus:
    def test_all_values_defined(self) -> None:
        values = {s.value for s in EventStatus}
        assert values == {"scheduled", "postponed", "cancelled", "finished"}

    def test_is_str(self) -> None:
        assert isinstance(EventStatus.SCHEDULED, str)
        assert EventStatus.SCHEDULED == "scheduled"


# ---------------------------------------------------------------------------
# Event
# ---------------------------------------------------------------------------


class TestEvent:
    def test_creation(self, australian_gp: Event) -> None:
        assert australian_gp.name == "Australian Grand Prix"
        assert australian_gp.season == 2025
        assert australian_gp.round == 1
        assert len(australian_gp.sessions) == 2
        assert australian_gp.event_uid == "f1-2025-01-aus@motorsport-calendar"

    def test_status_defaults_to_scheduled(self, australian_gp: Event) -> None:
        assert australian_gp.status == EventStatus.SCHEDULED

    def test_status_accepts_all_values(self, f1: Championship, albert_park: Circuit) -> None:
        for status in EventStatus:
            event = Event(
                championship=f1,
                season=2025,
                round=1,
                name="X",
                circuit=albert_park,
                event_uid="uid@test",
                status=status,
            )
            assert event.status == status

    def test_status_rejects_invalid_value(self, f1: Championship, albert_park: Circuit) -> None:
        with pytest.raises(ValidationError):
            Event(
                championship=f1,
                season=2025,
                round=1,
                name="X",
                circuit=albert_park,
                event_uid="uid@test",
                status="unknown",  # type: ignore[arg-type]
            )

    def test_event_uid_required(self, f1: Championship, albert_park: Circuit) -> None:
        with pytest.raises(ValidationError):
            Event(  # type: ignore[call-arg]
                championship=f1,
                season=2025,
                round=1,
                name="X",
                circuit=albert_park,
            )

    def test_event_uid_cannot_be_empty(self, f1: Championship, albert_park: Circuit) -> None:
        with pytest.raises(ValidationError):
            Event(
                championship=f1,
                season=2025,
                round=1,
                name="X",
                circuit=albert_park,
                event_uid="",
            )

    def test_sessions_are_tuple(self, australian_gp: Event) -> None:
        assert isinstance(australian_gp.sessions, tuple)

    def test_nested_championship(self, australian_gp: Event, f1: Championship) -> None:
        assert australian_gp.championship == f1
        assert australian_gp.championship.category == ChampionshipCategory.SINGLE_SEATER

    def test_nested_circuit(self, australian_gp: Event, albert_park: Circuit) -> None:
        assert australian_gp.circuit == albert_park
        assert australian_gp.circuit.timezone == "Australia/Melbourne"

    def test_empty_sessions_by_default(self, f1: Championship, albert_park: Circuit) -> None:
        event = Event(
            championship=f1,
            season=2025,
            round=2,
            name="Bahrain Grand Prix",
            circuit=albert_park,
            event_uid="f1-2025-02-bhr@motorsport-calendar",
        )
        assert event.sessions == ()

    def test_season_bounds(self, f1: Championship, albert_park: Circuit) -> None:
        with pytest.raises(ValidationError):
            Event(
                championship=f1,
                season=1900,
                round=1,
                name="X",
                circuit=albert_park,
                event_uid="uid@test",
            )

    def test_round_must_be_positive(self, f1: Championship, albert_park: Circuit) -> None:
        with pytest.raises(ValidationError):
            Event(
                championship=f1,
                season=2025,
                round=0,
                name="X",
                circuit=albert_park,
                event_uid="uid@test",
            )

    def test_immutable(self, australian_gp: Event) -> None:
        with pytest.raises(ValidationError):
            australian_gp.name = "Changed"
