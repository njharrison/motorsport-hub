"""Tests using real extracts from the sportstimes/f1 dataset.

Fixture files in tests/fixtures/real/ are minimal 2-event extracts copied
directly from the live sportstimes/f1 dataset. They MUST NOT be hand-crafted:
their value lies in preserving the exact key names, field types, and nesting
that the real dataset uses.

Convention for future providers
--------------------------------
Before writing any mock fixtures for a new support series:
  1. Download 1-2 events from the real dataset URL.
  2. Save them to tests/fixtures/real/<series>.json.
  3. Add a test class here that asserts the correct event/session counts.
Only then write the mock-based CLI tests.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

from typer.testing import CliRunner

from motorsport_calendar.cli import app
from motorsport_calendar.providers.formula2.sources.f1calendar import (
    _build_event as f2_build_event,
)
from motorsport_calendar.providers.formula2.sources.f1calendar import (
    _make_championship as f2_make_championship,
)

runner = CliRunner()

_FIXTURES_DIR = Path(__file__).parent / "fixtures" / "real"


def _load(name: str) -> dict[str, Any]:
    return json.loads((_FIXTURES_DIR / name).read_text())


# ---------------------------------------------------------------------------
# Formula 2 — 2025 season extract (2 events, "practice"/"sprint" key names)
# ---------------------------------------------------------------------------


class TestF2RealFixture:
    def test_fixture_has_races_key(self) -> None:
        payload = _load("formula2.json")
        assert "races" in payload
        assert "events" not in payload

    def test_fixture_has_2_events(self) -> None:
        assert len(_load("formula2.json")["races"]) == 2

    def test_cli_loads_2_events(self, tmp_path: Path) -> None:
        payload = _load("formula2.json")
        with patch(
            "motorsport_calendar.providers.formula2.sources.f1calendar.F1CalendarSource.fetch_json",
            new=AsyncMock(return_value=payload),
        ):
            result = runner.invoke(app, ["generate-f2", "2025", str(tmp_path / "f2.ics")])
        assert result.exit_code == 0, result.output
        assert "2 event" in result.output

    def test_each_event_has_4_sessions(self) -> None:
        payload = _load("formula2.json")
        champ = f2_make_championship(2025)
        for race in payload["races"]:
            event = f2_build_event(champ, race, 2025)
            assert len(event.sessions) == 4, (
                f"round {race['round']}: expected 4 sessions, got {len(event.sessions)}"
            )

    def test_ics_contains_8_vevents(self, tmp_path: Path) -> None:
        output = tmp_path / "f2-real.ics"
        payload = _load("formula2.json")
        with patch(
            "motorsport_calendar.providers.formula2.sources.f1calendar.F1CalendarSource.fetch_json",
            new=AsyncMock(return_value=payload),
        ):
            runner.invoke(app, ["generate-f2", "2025", str(output)])
        assert output.read_text().count("BEGIN:VEVENT") == 8


# ---------------------------------------------------------------------------
# Formula 3 — 2025 season extract (2 events, "practice"/"sprint" key names)
# ---------------------------------------------------------------------------


class TestF3RealFixture:
    def test_fixture_has_races_key(self) -> None:
        payload = _load("formula3.json")
        assert "races" in payload
        assert "events" not in payload

    def test_fixture_has_2_events(self) -> None:
        assert len(_load("formula3.json")["races"]) == 2

    def test_cli_loads_2_events(self, tmp_path: Path) -> None:
        payload = _load("formula3.json")
        with patch(
            "motorsport_calendar.providers.formula3.sources.f1calendar.F1CalendarSource.fetch_json",
            new=AsyncMock(return_value=payload),
        ):
            result = runner.invoke(app, ["generate-f3", "2025", str(tmp_path / "f3.ics")])
        assert result.exit_code == 0, result.output
        assert "2 event" in result.output

    def test_ics_contains_8_vevents(self, tmp_path: Path) -> None:
        output = tmp_path / "f3-real.ics"
        payload = _load("formula3.json")
        with patch(
            "motorsport_calendar.providers.formula3.sources.f1calendar.F1CalendarSource.fetch_json",
            new=AsyncMock(return_value=payload),
        ):
            runner.invoke(app, ["generate-f3", "2025", str(output)])
        assert output.read_text().count("BEGIN:VEVENT") == 8


# ---------------------------------------------------------------------------
# F1 Academy — 2025 season extract (2 events: fp1/qualifying1/race1/race2)
# ---------------------------------------------------------------------------


class TestF1AcademyRealFixture:
    def test_fixture_has_races_key(self) -> None:
        payload = _load("f1-academy.json")
        assert "races" in payload
        assert "events" not in payload

    def test_fixture_has_2_events(self) -> None:
        assert len(_load("f1-academy.json")["races"]) == 2

    def test_cli_loads_2_events(self, tmp_path: Path) -> None:
        payload = _load("f1-academy.json")
        with patch(
            "motorsport_calendar.providers.f1_academy.sources.f1calendar.F1CalendarSource.fetch_json",
            new=AsyncMock(return_value=payload),
        ):
            result = runner.invoke(app, ["generate-f1-academy", "2025", str(tmp_path / "f1a.ics")])
        assert result.exit_code == 0, result.output
        assert "2 event" in result.output

    def test_ics_contains_8_vevents(self, tmp_path: Path) -> None:
        output = tmp_path / "f1a-real.ics"
        payload = _load("f1-academy.json")
        with patch(
            "motorsport_calendar.providers.f1_academy.sources.f1calendar.F1CalendarSource.fetch_json",
            new=AsyncMock(return_value=payload),
        ):
            runner.invoke(app, ["generate-f1-academy", "2025", str(output)])
        # 2 events x 4 sessions each (fp1 + qualifying1 + race1 + race2)
        assert output.read_text().count("BEGIN:VEVENT") == 8


# ---------------------------------------------------------------------------
# Formula E — 2024/2025 season extract (2 events: practice1/practice2/
# qualifying/race — Sao Paulo round 1, Mexico City round 2)
# ---------------------------------------------------------------------------


class TestFormulaERealFixture:
    def test_fixture_has_races_key(self) -> None:
        payload = _load("formula-e.json")
        assert "races" in payload
        assert "events" not in payload

    def test_fixture_has_2_events(self) -> None:
        assert len(_load("formula-e.json")["races"]) == 2

    def test_cli_loads_2_events(self, tmp_path: Path) -> None:
        payload = _load("formula-e.json")
        with patch(
            "motorsport_calendar.providers.formula_e.sources.f1calendar."
            "F1CalendarSource.fetch_json",
            new=AsyncMock(return_value=payload),
        ):
            result = runner.invoke(app, ["generate-formula-e", "2025", str(tmp_path / "fe.ics")])
        assert result.exit_code == 0, result.output
        assert "2 event" in result.output

    def test_ics_contains_8_vevents(self, tmp_path: Path) -> None:
        output = tmp_path / "fe-real.ics"
        payload = _load("formula-e.json")
        with patch(
            "motorsport_calendar.providers.formula_e.sources.f1calendar."
            "F1CalendarSource.fetch_json",
            new=AsyncMock(return_value=payload),
        ):
            runner.invoke(app, ["generate-formula-e", "2025", str(output)])
        # 2 events x 4 sessions each (practice1 + practice2 + qualifying + race)
        assert output.read_text().count("BEGIN:VEVENT") == 8

    def test_event_names_are_already_complete_eprix_names(self, tmp_path: Path) -> None:
        """Unlike F1/F2/F3, Formula E event names never need a suffix — the
        dataset already returns complete names like "Sao Paulo ePrix"."""
        output = tmp_path / "fe-real.ics"
        payload = _load("formula-e.json")
        with patch(
            "motorsport_calendar.providers.formula_e.sources.f1calendar."
            "F1CalendarSource.fetch_json",
            new=AsyncMock(return_value=payload),
        ):
            runner.invoke(app, ["generate-formula-e", "2025", str(output)])
        content = output.read_text()
        assert "Sao Paulo ePrix" in content
        assert "Mexico City ePrix" in content
