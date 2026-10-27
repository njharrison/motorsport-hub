"""Shared pytest fixtures."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from motorsport_calendar.models import (
    Championship,
    ChampionshipCategory,
    Circuit,
    Event,
    Session,
    SessionType,
)

TZ = UTC

_REAL_FIXTURES_DIR = Path(__file__).parent / "fixtures" / "real"


def load_real_fixture(name: str) -> str:
    """Read a captured-HTML fixture from ``tests/fixtures/real/`` as text.

    Sprint 50 — factored out of 8 near-identical ``_load()`` module-level
    helpers (test_aco_sports_event_base.py, test_sro_timetable_base.py,
    test_cli_generate_{elms,mlmc,igtc,gtwc_america,gtwc_asia,gtwc_europe}.py)
    that all read the exact same directory. Plain function, not a
    ``@pytest.fixture``: callers use it at module import time to build
    module-level constants (e.g. ``_RACE_BARCELONA = load_real_fixture(...)``),
    before any fixture would be available.
    """
    return (_REAL_FIXTURES_DIR / name).read_text()


@pytest.fixture(autouse=True)
def _isolated_gui_prefs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Sprint 44: ``FavoritesService`` (and ``gui/preferences.py``
    generally) must never read/write the developer's real
    ``~/.config/motorsport-calendar/gui_prefs.json`` while running tests —
    autouse so every test gets an isolated, empty prefs file regardless of
    whether it explicitly cares about preferences/favorites (e.g.
    ``controller.get_upcoming_weekend``/``get_dashboard_data`` now read
    favorites internally). Individual tests that need specific prefs
    content still patch ``_PREFS_FILE`` themselves (see
    ``test_gui_preferences.py``); this fixture only sets the default any
    unrelated test would otherwise silently inherit from the real machine.
    """
    monkeypatch.setattr(
        "motorsport_calendar.gui.preferences._PREFS_FILE", tmp_path / "gui_prefs.json"
    )


@pytest.fixture
def f1() -> Championship:
    return Championship(
        id="f1",
        name="Formula 1 World Championship",
        category=ChampionshipCategory.SINGLE_SEATER,
    )


@pytest.fixture
def albert_park() -> Circuit:
    return Circuit(
        id="albert-park",
        name="Albert Park Circuit",
        city="Melbourne",
        country="Australia",
        timezone="Australia/Melbourne",
    )


@pytest.fixture
def race_session() -> Session:
    return Session(
        type=SessionType.RACE,
        start_datetime=datetime(2025, 3, 16, 5, 0, tzinfo=TZ),
        end_datetime=datetime(2025, 3, 16, 7, 0, tzinfo=TZ),
        title="Australian Grand Prix — Race",
        description="Round 1 of the 2025 season.",
    )


@pytest.fixture
def qualifying_session() -> Session:
    return Session(
        type=SessionType.QUALIFYING,
        start_datetime=datetime(2025, 3, 15, 7, 0, tzinfo=TZ),
        end_datetime=datetime(2025, 3, 15, 8, 0, tzinfo=TZ),
        title="Australian Grand Prix — Qualifying",
    )


@pytest.fixture
def australian_gp(
    f1: Championship,
    albert_park: Circuit,
    race_session: Session,
    qualifying_session: Session,
) -> Event:
    return Event(
        championship=f1,
        season=2025,
        round=1,
        name="Australian Grand Prix",
        circuit=albert_park,
        sessions=(qualifying_session, race_session),
        event_uid="f1-2025-01-aus@motorsport-calendar",
    )
