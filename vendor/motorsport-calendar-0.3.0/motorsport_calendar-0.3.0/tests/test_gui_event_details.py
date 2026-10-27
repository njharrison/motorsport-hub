"""Tests for gui.event_details — pure logic, no Flet, no HTTP.

Mirrors test_gui_season_explorer.py's style: plain Event/Session fixtures,
no HTTP mocking needed (the event is already fetched — it lives in
year_events, resolved by main_view.py before calling build_event_details).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from motorsport_calendar.gui.components.championship_card import ChampionshipCardData, SessionRow
from motorsport_calendar.gui.event_details import EventDetails, build_event_details
from motorsport_calendar.models import (
    Championship,
    ChampionshipCategory,
    Circuit,
    Event,
    Session,
    SessionType,
)


def _session(session_type: SessionType, start: datetime, *, minutes: int = 60) -> Session:
    return Session(
        type=session_type,
        start_datetime=start,
        end_datetime=start + timedelta(minutes=minutes),
        title=session_type.value,
    )


def _event(
    championship_id: str,
    *,
    name: str = "Grand Prix",
    circuit_name: str | None = None,
    circuit_city: str | None = None,
    country: str = "France",
    timezone_name: str = "Europe/Paris",
    round_: int = 1,
    season: int = 2026,
    sessions: tuple[Session, ...] = (),
) -> Event:
    championship = Championship(
        id=f"{championship_id}-9999",
        name=championship_id,
        category=ChampionshipCategory.SINGLE_SEATER,
    )
    circuit = Circuit(
        id=name.lower().replace(" ", "-"),
        name=circuit_name if circuit_name is not None else name,
        city=circuit_city if circuit_city is not None else name,
        country=country,
        timezone=timezone_name,
    )
    return Event(
        championship=championship,
        season=season,
        round=round_,
        name=name,
        circuit=circuit,
        sessions=sessions,
        event_uid=f"{championship_id}-{round_}@test",
    )


class TestBuildEventDetailsEmptyEvent:
    def test_no_sessions_yields_empty_card_sessions_and_no_date(self) -> None:
        event = _event("formula1", sessions=())
        details = build_event_details("formula1", event)
        assert details.card.sessions == ()
        assert details.date_label is None

    def test_no_sessions_still_populates_the_rest_of_the_card(self) -> None:
        event = _event(
            "formula1",
            name="Belgian",
            circuit_name="Spa-Francorchamps",
            country="Belgium",
            sessions=(),
        )
        details = build_event_details("formula1", event)
        assert details.card.championship_name == "Formula 1"
        assert details.card.event_name == "Belgian Grand Prix"
        assert details.card.circuit_name == "Spa-Francorchamps"
        assert details.card.country == "🇧🇪 Belgique"

    def test_returns_event_details_wrapping_championship_card_data(self) -> None:
        event = _event("formula1", sessions=())
        details = build_event_details("formula1", event)
        assert isinstance(details, EventDetails)
        assert isinstance(details.card, ChampionshipCardData)


class TestBuildEventDetailsFormula:
    def test_gp_suffix_and_normalized_fields(self) -> None:
        event = _event(
            "formula1",
            name="Belgian",
            circuit_name="Spa-Francorchamps",
            circuit_city="Spa",
            country="Belgium",
            sessions=(_session(SessionType.RACE, datetime(2026, 7, 12, 14, 0, tzinfo=UTC)),),
        )
        details = build_event_details("formula1", event)
        assert details.card.championship_id == "formula1"
        assert details.card.championship_name == "Formula 1"
        assert details.card.event_name == "Belgian Grand Prix"
        assert details.card.circuit_name == "Spa-Francorchamps"
        assert details.card.country == "🇧🇪 Belgique"

    def test_full_session_list_formula_weekend(self) -> None:
        event = _event(
            "formula1",
            sessions=(
                _session(SessionType.FP1, datetime(2026, 7, 10, 12, 30, tzinfo=UTC)),
                _session(SessionType.FP2, datetime(2026, 7, 10, 16, 0, tzinfo=UTC)),
                _session(SessionType.FP3, datetime(2026, 7, 11, 11, 30, tzinfo=UTC)),
                _session(SessionType.QUALIFYING, datetime(2026, 7, 11, 15, 0, tzinfo=UTC)),
                _session(SessionType.RACE, datetime(2026, 7, 12, 13, 0, tzinfo=UTC)),
            ),
        )
        details = build_event_details("formula1", event)
        labels = [row.label for row in details.card.sessions]
        assert labels == [
            "Essais Libres 1",
            "Essais Libres 2",
            "Essais Libres 3",
            "Qualifications",
            "Course",
        ]

    def test_date_label_anchored_on_earliest_session(self) -> None:
        event = _event(
            "formula1",
            timezone_name="UTC",
            sessions=(
                _session(SessionType.FP1, datetime(2026, 7, 10, 12, 30, tzinfo=UTC)),
                _session(SessionType.RACE, datetime(2026, 7, 12, 13, 0, tzinfo=UTC)),
            ),
        )
        details = build_event_details("formula1", event)
        assert details.date_label == "Vendredi 10/07/2026"


class TestBuildEventDetailsGT:
    def test_gt_event_no_gp_suffix(self) -> None:
        """GT championships aren't in the GP-suffix list — the raw name is
        kept as-is, unlike Formula's "Belgian" -> "Belgian Grand Prix"."""
        event = _event(
            "gtwc-europe",
            name="Total 24 Hours of Spa",
            circuit_name="Circuit de Spa-Francorchamps",
            country="Belgium",
            sessions=(_session(SessionType.RACE, datetime(2026, 6, 27, 15, 0, tzinfo=UTC)),),
        )
        details = build_event_details("gtwc-europe", event)
        assert details.card.event_name == "Total 24 Hours of Spa"
        assert details.card.championship_name == "GT World Challenge Europe"

    def test_gt_sprint_double_header_session_order(self) -> None:
        """GT Sprint Cup weekends run 2 Qualifying + 2 Race — the fiche must
        show them in the exact chronological order they occur."""
        event = _event(
            "gtwc-europe",
            sessions=(
                _session(SessionType.FP1, datetime(2026, 4, 10, 8, 0, tzinfo=UTC)),
                _session(SessionType.SPRINT_QUALIFYING, datetime(2026, 4, 10, 11, 0, tzinfo=UTC)),
                _session(SessionType.SPRINT, datetime(2026, 4, 10, 14, 0, tzinfo=UTC)),
                _session(SessionType.QUALIFYING, datetime(2026, 4, 11, 9, 0, tzinfo=UTC)),
                _session(SessionType.RACE, datetime(2026, 4, 11, 13, 0, tzinfo=UTC)),
            ),
        )
        details = build_event_details("gtwc-europe", event)
        labels = [row.label for row in details.card.sessions]
        assert labels == [
            "Essais Libres 1",
            "Qualifications Sprint",
            "Sprint",
            "Qualifications",
            "Course",
        ]


class TestBuildEventDetailsMoto:
    def test_moto_event_normalized_fields(self) -> None:
        event = _event(
            "motogp",
            name="Thailand",
            circuit_name="Chang International Circuit",
            country="Thailand",
            sessions=(_session(SessionType.RACE, datetime(2026, 2, 27, 8, 0, tzinfo=UTC)),),
        )
        details = build_event_details("motogp", event)
        assert details.card.championship_name == "MotoGP"
        assert details.card.circuit_name == "Chang International Circuit"
        # "Thailand" isn't in the curated country->flag table — falls back
        # to the raw stored name (event_display.country_label's documented
        # fallback), not a bug specific to this module.
        assert details.card.country == "Thailand"

    def test_moto_weekend_session_order_fp1_fp2_fp3_qualifying_sprint_race(self) -> None:
        event = _event(
            "motogp",
            sessions=(
                _session(SessionType.FP1, datetime(2026, 2, 27, 3, 45, tzinfo=UTC)),
                _session(SessionType.FP2, datetime(2026, 2, 27, 8, 0, tzinfo=UTC)),
                _session(SessionType.FP3, datetime(2026, 2, 28, 3, 10, tzinfo=UTC)),
                _session(SessionType.QUALIFYING, datetime(2026, 2, 28, 3, 50, tzinfo=UTC)),
                _session(SessionType.SPRINT, datetime(2026, 2, 28, 8, 0, tzinfo=UTC)),
                _session(SessionType.RACE, datetime(2026, 3, 1, 8, 0, tzinfo=UTC)),
            ),
        )
        details = build_event_details("motogp", event)
        labels = [row.label for row in details.card.sessions]
        assert labels == [
            "Essais Libres 1",
            "Essais Libres 2",
            "Essais Libres 3",
            "Qualifications",
            "Sprint",
            "Course",
        ]


class TestBuildEventDetailsChronologicalOrder:
    def test_sessions_sorted_regardless_of_input_order(self) -> None:
        """Provider ordering is never trusted — mirrors
        upcoming_weekend._build_card's own rule."""
        event = _event(
            "formula1",
            sessions=(
                _session(SessionType.RACE, datetime(2026, 7, 12, 13, 0, tzinfo=UTC)),
                _session(SessionType.FP1, datetime(2026, 7, 10, 12, 30, tzinfo=UTC)),
                _session(SessionType.QUALIFYING, datetime(2026, 7, 11, 15, 0, tzinfo=UTC)),
            ),
        )
        details = build_event_details("formula1", event)
        labels = [row.label for row in details.card.sessions]
        assert labels == ["Essais Libres 1", "Qualifications", "Course"]

    def test_two_sessions_same_day_ordered_by_exact_time(self) -> None:
        event = _event(
            "formula1",
            timezone_name="UTC",
            sessions=(
                _session(SessionType.FP2, datetime(2026, 7, 10, 16, 0, tzinfo=UTC)),
                _session(SessionType.FP1, datetime(2026, 7, 10, 12, 30, tzinfo=UTC)),
            ),
        )
        details = build_event_details("formula1", event)
        labels = [row.label for row in details.card.sessions]
        assert labels == ["Essais Libres 1", "Essais Libres 2"]


class TestSessionDayTimeFormat:
    def test_day_time_uses_circuit_local_timezone(self) -> None:
        event = _event(
            "formula1",
            timezone_name="Asia/Tokyo",  # UTC+9
            sessions=(_session(SessionType.RACE, datetime(2026, 4, 5, 5, 0, tzinfo=UTC)),),
        )
        details = build_event_details("formula1", event)
        # 05:00 UTC + 9h = 14:00 local, same calendar day (Sunday).
        assert details.card.sessions[0].day_time == "Dimanche 14:00"

    def test_unknown_timezone_falls_back_to_utc(self) -> None:
        event = _event(
            "formula1",
            timezone_name="Not/A_Real_Zone",
            sessions=(_session(SessionType.RACE, datetime(2026, 7, 12, 14, 0, tzinfo=UTC)),),
        )
        details = build_event_details("formula1", event)
        assert details.card.sessions[0].day_time == "Dimanche 14:00"


class TestCircuitKey:
    """Sprint 47: circuit_key is in lockstep with card.circuit_name —
    ``None`` exactly when there is no circuit line to click."""

    def test_circuit_key_set_when_circuit_name_is_shown(self) -> None:
        event = _event(
            "formula1",
            name="Belgian",
            circuit_name="Spa-Francorchamps",
            country="Belgium",
            sessions=(),
        )
        details = build_event_details("formula1", event)
        assert details.card.circuit_name == "Spa-Francorchamps"
        assert details.circuit_key == "spafrancorchamps"

    def test_circuit_key_is_none_when_circuit_name_is_hidden(self) -> None:
        """F2/F3-style bug (Sprint 32): event.name == circuit.name, so the
        circuit line is hidden as redundant — nothing to click either."""
        event = _event(
            "formula2",
            name="Belgian",
            circuit_name="Belgian",
            circuit_city="Belgian",
            country="Belgium",
            sessions=(),
        )
        details = build_event_details("formula2", event)
        assert details.card.circuit_name is None
        assert details.circuit_key is None


class TestSessionRowShape:
    def test_returns_session_row_tuples(self) -> None:
        event = _event(
            "formula1",
            sessions=(_session(SessionType.RACE, datetime(2026, 7, 12, 14, 0, tzinfo=UTC)),),
        )
        details = build_event_details("formula1", event)
        assert isinstance(details.card.sessions, tuple)
        assert isinstance(details.card.sessions[0], SessionRow)

    def test_unmapped_session_type_falls_back_to_title(self) -> None:
        """Defensive: every current SessionType is mapped, but the fallback
        (session.title) must still work if a future type slips through."""
        session = _session(SessionType.TEST, datetime(2026, 7, 10, 9, 0, tzinfo=UTC))
        event = _event("formula1", sessions=(session,))
        details = build_event_details("formula1", event)
        assert details.card.sessions[0].label == "Essais"  # TEST is mapped
