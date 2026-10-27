"""Integration tests for the `motocal generate-worldsbk` CLI command.

Strategy: patch OfficialWorldSbkSource.get_season with AsyncMock so no real HTTP
calls are made. The rest of the pipeline (WorldSbkProvider, IcsExporter) runs for
real.

For the NotImplementedError tests: no patch needed — the default stub raises it.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
from typer.testing import CliRunner

from motorsport_calendar.cli import app
from motorsport_calendar.models import (
    Championship,
    ChampionshipCategory,
    Circuit,
    Event,
    Session,
    SessionType,
)
from motorsport_calendar.providers.worldsbk.sources.official import OfficialWorldSbkSource

runner = CliRunner()

# ---------------------------------------------------------------------------
# Minimal sample data — representative WorldSBK season
# ---------------------------------------------------------------------------

_CHAMPIONSHIP = Championship(
    id="worldsbk-2024",
    name="FIM Superbike World Championship",
    category=ChampionshipCategory.MOTORBIKE,
)

_WORLDSBK_EVENTS = [
    Event(
        event_uid="worldsbk-2024-01-phillip-island",
        championship=_CHAMPIONSHIP,
        season=2024,
        round=1,
        name="Phillip Island Round",
        circuit=Circuit(
            id="phillip-island",
            name="Phillip Island Grand Prix Circuit",
            city="Phillip Island",
            country="Australia",
            timezone="Australia/Melbourne",
        ),
        sessions=(
            Session(
                type=SessionType.RACE,
                title="Race 1",
                start_datetime=datetime(2024, 2, 25, 4, 0, tzinfo=UTC),
                end_datetime=datetime(2024, 2, 25, 4, 35, tzinfo=UTC),
            ),
        ),
    ),
    Event(
        event_uid="worldsbk-2024-02-barcelona",
        championship=_CHAMPIONSHIP,
        season=2024,
        round=2,
        name="Catalunya Round",
        circuit=Circuit(
            id="catalunya",
            name="Circuit de Barcelona-Catalunya",
            city="Barcelona",
            country="Spain",
            timezone="Europe/Madrid",
        ),
        sessions=(
            Session(
                type=SessionType.QUALIFYING,
                title="Superpole",
                start_datetime=datetime(2024, 4, 6, 11, 0, tzinfo=UTC),
                end_datetime=datetime(2024, 4, 6, 11, 30, tzinfo=UTC),
            ),
            Session(
                type=SessionType.RACE,
                title="Race 1",
                start_datetime=datetime(2024, 4, 6, 14, 0, tzinfo=UTC),
                end_datetime=datetime(2024, 4, 6, 14, 35, tzinfo=UTC),
            ),
        ),
    ),
]

_SESSIONS_COUNT = sum(len(e.sessions) for e in _WORLDSBK_EVENTS)  # 3


def _mock_get_season(events: list) -> AsyncMock:
    """Retourne un AsyncMock qui répond immédiatement avec la liste d'événements."""
    return AsyncMock(return_value=events)


# ---------------------------------------------------------------------------
# Happy-path tests
# ---------------------------------------------------------------------------


class TestGenerateWorldSbkHappyPath:
    def test_exit_code_is_zero(self, tmp_path: Path) -> None:
        mock = _mock_get_season(_WORLDSBK_EVENTS)
        with patch.object(OfficialWorldSbkSource, "get_season", mock):
            result = runner.invoke(app, ["generate-worldsbk", "2024", str(tmp_path / "cal.ics")])
        assert result.exit_code == 0

    def test_ics_file_is_created(self, tmp_path: Path) -> None:
        output = tmp_path / "worldsbk-2024.ics"
        mock = _mock_get_season(_WORLDSBK_EVENTS)
        with patch.object(OfficialWorldSbkSource, "get_season", mock):
            runner.invoke(app, ["generate-worldsbk", "2024", str(output)])
        assert output.exists()
        assert output.stat().st_size > 0

    def test_ics_file_contains_vcalendar(self, tmp_path: Path) -> None:
        output = tmp_path / "worldsbk-2024.ics"
        mock = _mock_get_season(_WORLDSBK_EVENTS)
        with patch.object(OfficialWorldSbkSource, "get_season", mock):
            runner.invoke(app, ["generate-worldsbk", "2024", str(output)])
        content = output.read_text(encoding="utf-8")
        assert "BEGIN:VCALENDAR" in content
        assert "END:VCALENDAR" in content

    def test_ics_file_contains_one_vevent_per_session(self, tmp_path: Path) -> None:
        output = tmp_path / "worldsbk-2024.ics"
        mock = _mock_get_season(_WORLDSBK_EVENTS)
        with patch.object(OfficialWorldSbkSource, "get_season", mock):
            runner.invoke(app, ["generate-worldsbk", "2024", str(output)])
        content = output.read_text(encoding="utf-8")
        assert content.count("BEGIN:VEVENT") == _SESSIONS_COUNT

    def test_ics_contains_circuit_locations(self, tmp_path: Path) -> None:
        output = tmp_path / "worldsbk-2024.ics"
        mock = _mock_get_season(_WORLDSBK_EVENTS)
        with patch.object(OfficialWorldSbkSource, "get_season", mock):
            runner.invoke(app, ["generate-worldsbk", "2024", str(output)])
        content = output.read_text(encoding="utf-8")
        assert "Phillip Island Grand Prix Circuit" in content
        assert "Circuit de Barcelona-Catalunya" in content

    def test_get_season_called_once(self, tmp_path: Path) -> None:
        mock = _mock_get_season(_WORLDSBK_EVENTS)
        with patch.object(OfficialWorldSbkSource, "get_season", mock):
            runner.invoke(app, ["generate-worldsbk", "2024", str(tmp_path / "cal.ics")])
        assert mock.call_count == 1

    def test_get_season_receives_correct_year(self, tmp_path: Path) -> None:
        mock = _mock_get_season(_WORLDSBK_EVENTS)
        with patch.object(OfficialWorldSbkSource, "get_season", mock):
            runner.invoke(app, ["generate-worldsbk", "2025", str(tmp_path / "cal.ics")])
        mock.assert_called_once_with(2025)

    def test_empty_season_writes_calendar_with_no_vevents(self, tmp_path: Path) -> None:
        output = tmp_path / "empty.ics"
        mock = _mock_get_season([])
        with patch.object(OfficialWorldSbkSource, "get_season", mock):
            result = runner.invoke(app, ["generate-worldsbk", "2025", str(output)])
        assert result.exit_code == 0
        assert output.exists()
        content = output.read_text(encoding="utf-8")
        assert "BEGIN:VCALENDAR" in content
        assert "BEGIN:VEVENT" not in content


# ---------------------------------------------------------------------------
# Error-path tests
# ---------------------------------------------------------------------------


class TestGenerateWorldSbkErrors:
    def test_not_implemented_exits_with_code_1(self, tmp_path: Path) -> None:
        """Sans mock : le stub OfficialWorldSbkSource lève NotImplementedError."""
        result = runner.invoke(app, ["generate-worldsbk", "2024", str(tmp_path / "cal.ics")])
        assert result.exit_code == 1

    def test_not_implemented_does_not_create_file(self, tmp_path: Path) -> None:
        output = tmp_path / "cal.ics"
        runner.invoke(app, ["generate-worldsbk", "2024", str(output)])
        assert not output.exists()

    def test_http_error_exits_with_code_1(self, tmp_path: Path) -> None:
        request = httpx.Request("GET", "https://example.com/worldsbk")
        response = httpx.Response(503, request=request)
        mock = AsyncMock(
            side_effect=httpx.HTTPStatusError("503", request=request, response=response)
        )
        with patch.object(OfficialWorldSbkSource, "get_season", mock):
            result = runner.invoke(app, ["generate-worldsbk", "2024", str(tmp_path / "cal.ics")])
        assert result.exit_code == 1

    def test_http_error_does_not_create_file(self, tmp_path: Path) -> None:
        output = tmp_path / "cal.ics"
        request = httpx.Request("GET", "https://example.com/worldsbk")
        response = httpx.Response(404, request=request)
        mock = AsyncMock(
            side_effect=httpx.HTTPStatusError("404", request=request, response=response)
        )
        with patch.object(OfficialWorldSbkSource, "get_season", mock):
            runner.invoke(app, ["generate-worldsbk", "2024", str(output)])
        assert not output.exists()

    def test_timeout_exits_with_code_1(self, tmp_path: Path) -> None:
        request = httpx.Request("GET", "https://example.com/worldsbk")
        mock = AsyncMock(side_effect=httpx.TimeoutException("timeout", request=request))
        with patch.object(OfficialWorldSbkSource, "get_season", mock):
            result = runner.invoke(app, ["generate-worldsbk", "2024", str(tmp_path / "cal.ics")])
        assert result.exit_code == 1

    def test_timeout_does_not_create_file(self, tmp_path: Path) -> None:
        output = tmp_path / "cal.ics"
        request = httpx.Request("GET", "https://example.com/worldsbk")
        mock = AsyncMock(side_effect=httpx.TimeoutException("timeout", request=request))
        with patch.object(OfficialWorldSbkSource, "get_season", mock):
            runner.invoke(app, ["generate-worldsbk", "2024", str(output)])
        assert not output.exists()


# ---------------------------------------------------------------------------
# --refresh flag
# ---------------------------------------------------------------------------


class TestGenerateWorldSbkRefresh:
    def test_refresh_flag_exits_zero(self, tmp_path: Path) -> None:
        mock = _mock_get_season(_WORLDSBK_EVENTS)
        with patch.object(OfficialWorldSbkSource, "get_season", mock):
            result = runner.invoke(
                app, ["generate-worldsbk", "2024", str(tmp_path / "cal.ics"), "--refresh"]
            )
        assert result.exit_code == 0

    def test_refresh_flag_creates_ics_file(self, tmp_path: Path) -> None:
        output = tmp_path / "worldsbk-refresh.ics"
        mock = _mock_get_season(_WORLDSBK_EVENTS)
        with patch.object(OfficialWorldSbkSource, "get_season", mock):
            runner.invoke(app, ["generate-worldsbk", "2024", str(output), "--refresh"])
        assert output.exists()
