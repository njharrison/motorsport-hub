"""Integration tests for the `motocal generate-f1` CLI command.

Strategy: patch OpenF1Source._get_json with AsyncMock so no real HTTP calls
are made. The rest of the pipeline (Formula1Provider, IcsExporter) runs for real.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
from typer.testing import CliRunner

from motorsport_calendar.cli import app
from motorsport_calendar.providers.formula1.sources.openf1 import OpenF1Source

runner = CliRunner()

# ---------------------------------------------------------------------------
# Minimal sample data — mirrors the OpenF1 API response shape
# ---------------------------------------------------------------------------

_MEETINGS = [
    {
        "meeting_key": 1217,
        "meeting_name": "Bahrain Grand Prix",
        "location": "Sakhir",
        "country_name": "Bahrain",
        "circuit_short_name": "Sakhir",
        "circuit_key": 1,
        "year": 2024,
        "date_start": "2024-02-29T09:00:00+00:00",
    },
    {
        "meeting_key": 1218,
        "meeting_name": "Saudi Arabian Grand Prix",
        "location": "Jeddah",
        "country_name": "Saudi Arabia",
        "circuit_short_name": "Jeddah",
        "circuit_key": 2,
        "year": 2024,
        "date_start": "2024-03-07T09:00:00+00:00",
    },
]

_SESSIONS = [
    {
        "session_key": 9472,
        "meeting_key": 1217,
        "session_name": "Race",
        "date_start": "2024-03-02T15:00:00+00:00",
        "date_end": "2024-03-02T17:00:00+00:00",
    },
    {
        "session_key": 9473,
        "meeting_key": 1217,
        "session_name": "Qualifying",
        "date_start": "2024-03-01T15:00:00+00:00",
        "date_end": "2024-03-01T16:00:00+00:00",
    },
    {
        "session_key": 9490,
        "meeting_key": 1218,
        "session_name": "Race",
        "date_start": "2024-03-09T18:00:00+00:00",
        "date_end": "2024-03-09T20:00:00+00:00",
    },
]


def _mock_get_json(meetings: list, sessions: list) -> AsyncMock:
    """Return an AsyncMock that yields meetings on the first call, sessions on the second."""
    return AsyncMock(side_effect=[meetings, sessions])


# ---------------------------------------------------------------------------
# Happy-path tests
# ---------------------------------------------------------------------------


class TestGenerateF1HappyPath:
    def test_exit_code_is_zero(self, tmp_path: Path) -> None:
        mock = _mock_get_json(_MEETINGS, _SESSIONS)
        with patch.object(OpenF1Source, "_get_json", mock):
            result = runner.invoke(app, ["generate-f1", "2024", str(tmp_path / "cal.ics")])
        assert result.exit_code == 0

    def test_ics_file_is_created(self, tmp_path: Path) -> None:
        output = tmp_path / "f1-2024.ics"
        mock = _mock_get_json(_MEETINGS, _SESSIONS)
        with patch.object(OpenF1Source, "_get_json", mock):
            runner.invoke(app, ["generate-f1", "2024", str(output)])
        assert output.exists()
        assert output.stat().st_size > 0

    def test_ics_file_contains_vcalendar(self, tmp_path: Path) -> None:
        output = tmp_path / "f1-2024.ics"
        mock = _mock_get_json(_MEETINGS, _SESSIONS)
        with patch.object(OpenF1Source, "_get_json", mock):
            runner.invoke(app, ["generate-f1", "2024", str(output)])
        content = output.read_text(encoding="utf-8")
        assert "BEGIN:VCALENDAR" in content
        assert "END:VCALENDAR" in content

    def test_ics_file_contains_vevents(self, tmp_path: Path) -> None:
        output = tmp_path / "f1-2024.ics"
        mock = _mock_get_json(_MEETINGS, _SESSIONS)
        with patch.object(OpenF1Source, "_get_json", mock):
            runner.invoke(app, ["generate-f1", "2024", str(output)])
        content = output.read_text(encoding="utf-8")
        assert content.count("BEGIN:VEVENT") == len(_SESSIONS)

    def test_ics_contains_circuit_locations(self, tmp_path: Path) -> None:
        # LOCATION field in VEVENT is "{city}, {country}" — circuit name, not GP name
        output = tmp_path / "f1-2024.ics"
        mock = _mock_get_json(_MEETINGS, _SESSIONS)
        with patch.object(OpenF1Source, "_get_json", mock):
            runner.invoke(app, ["generate-f1", "2024", str(output)])
        content = output.read_text(encoding="utf-8")
        assert "Sakhir" in content
        assert "Jeddah" in content

    def test_get_json_called_twice(self, tmp_path: Path) -> None:
        mock = _mock_get_json(_MEETINGS, _SESSIONS)
        with patch.object(OpenF1Source, "_get_json", mock):
            runner.invoke(app, ["generate-f1", "2024", str(tmp_path / "cal.ics")])
        assert mock.call_count == 2

    def test_empty_season_writes_calendar_with_no_events(self, tmp_path: Path) -> None:
        output = tmp_path / "empty.ics"
        mock = _mock_get_json([], [])
        with patch.object(OpenF1Source, "_get_json", mock):
            result = runner.invoke(app, ["generate-f1", "2025", str(output)])
        assert result.exit_code == 0
        assert output.exists()
        content = output.read_text(encoding="utf-8")
        assert "BEGIN:VCALENDAR" in content
        assert "BEGIN:VEVENT" not in content


# ---------------------------------------------------------------------------
# Error-path tests
# ---------------------------------------------------------------------------


class TestGenerateF1Errors:
    def test_http_error_exits_with_code_1(self, tmp_path: Path) -> None:
        request = httpx.Request("GET", "https://api.openf1.org/v1/meetings")
        response = httpx.Response(503, request=request)
        mock = AsyncMock(
            side_effect=httpx.HTTPStatusError("503", request=request, response=response)
        )
        with patch.object(OpenF1Source, "_get_json", mock):
            result = runner.invoke(app, ["generate-f1", "2024", str(tmp_path / "cal.ics")])
        assert result.exit_code == 1

    def test_http_error_does_not_create_file(self, tmp_path: Path) -> None:
        output = tmp_path / "cal.ics"
        request = httpx.Request("GET", "https://api.openf1.org/v1/meetings")
        response = httpx.Response(404, request=request)
        mock = AsyncMock(
            side_effect=httpx.HTTPStatusError("404", request=request, response=response)
        )
        with patch.object(OpenF1Source, "_get_json", mock):
            runner.invoke(app, ["generate-f1", "2024", str(output)])
        assert not output.exists()

    def test_timeout_exits_with_code_1(self, tmp_path: Path) -> None:
        request = httpx.Request("GET", "https://api.openf1.org/v1/meetings")
        mock = AsyncMock(side_effect=httpx.TimeoutException("timeout", request=request))
        with patch.object(OpenF1Source, "_get_json", mock):
            result = runner.invoke(app, ["generate-f1", "2024", str(tmp_path / "cal.ics")])
        assert result.exit_code == 1

    def test_timeout_does_not_create_file(self, tmp_path: Path) -> None:
        output = tmp_path / "cal.ics"
        request = httpx.Request("GET", "https://api.openf1.org/v1/meetings")
        mock = AsyncMock(side_effect=httpx.TimeoutException("timeout", request=request))
        with patch.object(OpenF1Source, "_get_json", mock):
            runner.invoke(app, ["generate-f1", "2024", str(output)])
        assert not output.exists()


# ---------------------------------------------------------------------------
# --refresh flag
# ---------------------------------------------------------------------------


class TestGenerateF1Refresh:
    def test_refresh_flag_exits_zero(self, tmp_path: Path) -> None:
        mock = _mock_get_json(_MEETINGS, _SESSIONS)
        with patch.object(OpenF1Source, "_get_json", mock):
            result = runner.invoke(
                app, ["generate-f1", "2024", str(tmp_path / "cal.ics"), "--refresh"]
            )
        assert result.exit_code == 0

    def test_refresh_flag_creates_ics_file(self, tmp_path: Path) -> None:
        output = tmp_path / "f1-refresh.ics"
        mock = _mock_get_json(_MEETINGS, _SESSIONS)
        with patch.object(OpenF1Source, "_get_json", mock):
            runner.invoke(app, ["generate-f1", "2024", str(output), "--refresh"])
        assert output.exists()

    def test_refresh_passes_flag_to_source(self, tmp_path: Path) -> None:
        """Vérifie que refresh=True est transmis à OpenF1Source."""
        mock = _mock_get_json(_MEETINGS, _SESSIONS)
        captured: list[bool] = []

        original_init = OpenF1Source.__init__

        def patched_init(self, client=None, cache=None, *, refresh=False):
            captured.append(refresh)
            original_init(self, client=client, cache=cache, refresh=refresh)

        with (
            patch.object(OpenF1Source, "__init__", patched_init),
            patch.object(OpenF1Source, "_get_json", mock),
        ):
            runner.invoke(app, ["generate-f1", "2024", str(tmp_path / "cal.ics"), "--refresh"])

        assert captured == [True]

    def test_no_refresh_flag_passes_false_to_source(self, tmp_path: Path) -> None:
        mock = _mock_get_json(_MEETINGS, _SESSIONS)
        captured: list[bool] = []

        original_init = OpenF1Source.__init__

        def patched_init(self, client=None, cache=None, *, refresh=False):
            captured.append(refresh)
            original_init(self, client=client, cache=cache, refresh=refresh)

        with (
            patch.object(OpenF1Source, "__init__", patched_init),
            patch.object(OpenF1Source, "_get_json", mock),
        ):
            runner.invoke(app, ["generate-f1", "2024", str(tmp_path / "cal.ics")])

        assert captured == [False]
