"""Integration tests for the `motocal generate-wec` CLI command.

Strategy: patch OfficialWecSource.get_season with AsyncMock so no real HTTP calls
are made. The rest of the pipeline (WecProvider, IcsExporter) runs for real.

OfficialWecSource is a real implementation since Sprint 48 (fiawec.com JSON-LD,
see tests/test_wec_provider.py::TestOfficialWecSourceRealFixtures for its own
fixture-driven parsing tests) — every test here still mocks get_season to keep
this file network-free, same as before.
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
from motorsport_calendar.providers.wec.sources.official import OfficialWecSource

runner = CliRunner()

# ---------------------------------------------------------------------------
# Minimal sample data — representative WEC season
# ---------------------------------------------------------------------------

_CHAMPIONSHIP = Championship(
    id="wec-2024",
    name="FIA World Endurance Championship",
    category=ChampionshipCategory.ENDURANCE,
)

_WEC_EVENTS = [
    Event(
        event_uid="wec-2024-01-sebring",
        championship=_CHAMPIONSHIP,
        season=2024,
        round=1,
        name="1000 Miles of Sebring",
        circuit=Circuit(
            id="sebring",
            name="Sebring International Raceway",
            city="Sebring",
            country="USA",
            timezone="America/New_York",
        ),
        sessions=(
            Session(
                type=SessionType.RACE,
                title="Race",
                start_datetime=datetime(2024, 3, 16, 16, 0, tzinfo=UTC),
                end_datetime=datetime(2024, 3, 16, 22, 0, tzinfo=UTC),
            ),
        ),
    ),
    Event(
        event_uid="wec-2024-02-spa",
        championship=_CHAMPIONSHIP,
        season=2024,
        round=2,
        name="6 Hours of Spa-Francorchamps",
        circuit=Circuit(
            id="spa",
            name="Circuit de Spa-Francorchamps",
            city="Spa",
            country="Belgium",
            timezone="Europe/Brussels",
        ),
        sessions=(
            Session(
                type=SessionType.HYPERPOLE,
                title="Hyperpole",
                start_datetime=datetime(2024, 5, 10, 9, 0, tzinfo=UTC),
                end_datetime=datetime(2024, 5, 10, 9, 30, tzinfo=UTC),
            ),
            Session(
                type=SessionType.RACE,
                title="Race",
                start_datetime=datetime(2024, 5, 11, 13, 0, tzinfo=UTC),
                end_datetime=datetime(2024, 5, 11, 19, 0, tzinfo=UTC),
            ),
        ),
    ),
]

_SESSIONS_COUNT = sum(len(e.sessions) for e in _WEC_EVENTS)  # 3


def _mock_get_season(events: list) -> AsyncMock:
    """Retourne un AsyncMock qui répond immédiatement avec la liste d'événements."""
    return AsyncMock(return_value=events)


# ---------------------------------------------------------------------------
# Happy-path tests
# ---------------------------------------------------------------------------


class TestGenerateWecHappyPath:
    def test_exit_code_is_zero(self, tmp_path: Path) -> None:
        mock = _mock_get_season(_WEC_EVENTS)
        with patch.object(OfficialWecSource, "get_season", mock):
            result = runner.invoke(app, ["generate-wec", "2024", str(tmp_path / "cal.ics")])
        assert result.exit_code == 0

    def test_ics_file_is_created(self, tmp_path: Path) -> None:
        output = tmp_path / "wec-2024.ics"
        mock = _mock_get_season(_WEC_EVENTS)
        with patch.object(OfficialWecSource, "get_season", mock):
            runner.invoke(app, ["generate-wec", "2024", str(output)])
        assert output.exists()
        assert output.stat().st_size > 0

    def test_ics_file_contains_vcalendar(self, tmp_path: Path) -> None:
        output = tmp_path / "wec-2024.ics"
        mock = _mock_get_season(_WEC_EVENTS)
        with patch.object(OfficialWecSource, "get_season", mock):
            runner.invoke(app, ["generate-wec", "2024", str(output)])
        content = output.read_text(encoding="utf-8")
        assert "BEGIN:VCALENDAR" in content
        assert "END:VCALENDAR" in content

    def test_ics_file_contains_one_vevent_per_session(self, tmp_path: Path) -> None:
        output = tmp_path / "wec-2024.ics"
        mock = _mock_get_season(_WEC_EVENTS)
        with patch.object(OfficialWecSource, "get_season", mock):
            runner.invoke(app, ["generate-wec", "2024", str(output)])
        content = output.read_text(encoding="utf-8")
        assert content.count("BEGIN:VEVENT") == _SESSIONS_COUNT

    def test_ics_contains_circuit_locations(self, tmp_path: Path) -> None:
        output = tmp_path / "wec-2024.ics"
        mock = _mock_get_season(_WEC_EVENTS)
        with patch.object(OfficialWecSource, "get_season", mock):
            runner.invoke(app, ["generate-wec", "2024", str(output)])
        content = output.read_text(encoding="utf-8")
        assert "Sebring" in content
        assert "Belgium" in content

    def test_get_season_called_once(self, tmp_path: Path) -> None:
        mock = _mock_get_season(_WEC_EVENTS)
        with patch.object(OfficialWecSource, "get_season", mock):
            runner.invoke(app, ["generate-wec", "2024", str(tmp_path / "cal.ics")])
        assert mock.call_count == 1

    def test_get_season_receives_correct_year(self, tmp_path: Path) -> None:
        mock = _mock_get_season(_WEC_EVENTS)
        with patch.object(OfficialWecSource, "get_season", mock):
            runner.invoke(app, ["generate-wec", "2025", str(tmp_path / "cal.ics")])
        mock.assert_called_once_with(2025)

    def test_empty_season_writes_calendar_with_no_vevents(self, tmp_path: Path) -> None:
        output = tmp_path / "empty.ics"
        mock = _mock_get_season([])
        with patch.object(OfficialWecSource, "get_season", mock):
            result = runner.invoke(app, ["generate-wec", "2025", str(output)])
        assert result.exit_code == 0
        assert output.exists()
        content = output.read_text(encoding="utf-8")
        assert "BEGIN:VCALENDAR" in content
        assert "BEGIN:VEVENT" not in content


# ---------------------------------------------------------------------------
# Error-path tests
# ---------------------------------------------------------------------------


class TestGenerateWecErrors:
    def test_http_error_exits_with_code_1(self, tmp_path: Path) -> None:
        request = httpx.Request("GET", "https://example.com/wec")
        response = httpx.Response(503, request=request)
        mock = AsyncMock(
            side_effect=httpx.HTTPStatusError("503", request=request, response=response)
        )
        with patch.object(OfficialWecSource, "get_season", mock):
            result = runner.invoke(app, ["generate-wec", "2024", str(tmp_path / "cal.ics")])
        assert result.exit_code == 1

    def test_http_error_does_not_create_file(self, tmp_path: Path) -> None:
        output = tmp_path / "cal.ics"
        request = httpx.Request("GET", "https://example.com/wec")
        response = httpx.Response(404, request=request)
        mock = AsyncMock(
            side_effect=httpx.HTTPStatusError("404", request=request, response=response)
        )
        with patch.object(OfficialWecSource, "get_season", mock):
            runner.invoke(app, ["generate-wec", "2024", str(output)])
        assert not output.exists()

    def test_timeout_exits_with_code_1(self, tmp_path: Path) -> None:
        request = httpx.Request("GET", "https://example.com/wec")
        mock = AsyncMock(side_effect=httpx.TimeoutException("timeout", request=request))
        with patch.object(OfficialWecSource, "get_season", mock):
            result = runner.invoke(app, ["generate-wec", "2024", str(tmp_path / "cal.ics")])
        assert result.exit_code == 1

    def test_timeout_does_not_create_file(self, tmp_path: Path) -> None:
        output = tmp_path / "cal.ics"
        request = httpx.Request("GET", "https://example.com/wec")
        mock = AsyncMock(side_effect=httpx.TimeoutException("timeout", request=request))
        with patch.object(OfficialWecSource, "get_season", mock):
            runner.invoke(app, ["generate-wec", "2024", str(output)])
        assert not output.exists()


# ---------------------------------------------------------------------------
# --refresh flag
# ---------------------------------------------------------------------------


class TestGenerateWecRefresh:
    def test_refresh_flag_exits_zero(self, tmp_path: Path) -> None:
        mock = _mock_get_season(_WEC_EVENTS)
        with patch.object(OfficialWecSource, "get_season", mock):
            result = runner.invoke(
                app, ["generate-wec", "2024", str(tmp_path / "cal.ics"), "--refresh"]
            )
        assert result.exit_code == 0

    def test_refresh_flag_creates_ics_file(self, tmp_path: Path) -> None:
        output = tmp_path / "wec-refresh.ics"
        mock = _mock_get_season(_WEC_EVENTS)
        with patch.object(OfficialWecSource, "get_season", mock):
            runner.invoke(app, ["generate-wec", "2024", str(output), "--refresh"])
        assert output.exists()
