"""CLI integration tests for `motocal generate-f3`."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

from typer.testing import CliRunner

from motorsport_calendar.cli import app

runner = CliRunner()

# ---------------------------------------------------------------------------
# Shared test fixtures
# F3 uses "practice" (not "fp1") and "sprint" (not "sprintRace").
# ---------------------------------------------------------------------------

_BAHRAIN_EVENT: dict[str, Any] = {
    "name": "Bahrain Grand Prix",
    "location": "Sakhir",
    "round": 1,
    "slug": "bahrain",
    "localeKey": "bahrain",
    "sessions": {
        "practice": "2025-02-27T11:05:00Z",
        "qualifying": "2025-02-28T12:10:00Z",
        "sprint": "2025-03-01T09:05:00Z",
        "feature": "2025-03-02T10:05:00Z",
    },
}

_MONACO_EVENT: dict[str, Any] = {
    "name": "Monaco Grand Prix",
    "location": "Monte Carlo",
    "round": 4,
    "slug": "monaco",
    "localeKey": "monaco",
    "sessions": {
        "qualifying": "2025-05-23T13:00:00Z",
        "sprint": "2025-05-24T10:35:00Z",
        "feature": "2025-05-25T09:05:00Z",
    },
}

_F1CALENDAR_ONE_RACE: dict[str, Any] = {
    "name": "Formula 3",
    "races": [_BAHRAIN_EVENT],
}

_F1CALENDAR_TWO_RACES: dict[str, Any] = {
    "name": "Formula 3",
    "races": [_BAHRAIN_EVENT, _MONACO_EVENT],
}

_F1CALENDAR_EMPTY: dict[str, Any] = {
    "name": "Formula 3",
    "races": [],
}


def _run_generate_f3(
    year: int,
    output: Path,
    fetch_json_return: Any = _F1CALENDAR_ONE_RACE,
    extra_args: list[str] | None = None,
) -> Any:
    """Invoke `generate-f3` with a mocked F1CalendarSource.fetch_json."""
    args = ["generate-f3", str(year), str(output)] + (extra_args or [])
    with patch(
        "motorsport_calendar.providers.formula3.sources.f1calendar.F1CalendarSource.fetch_json",
        new=AsyncMock(return_value=fetch_json_return),
    ):
        return runner.invoke(app, args)


# ---------------------------------------------------------------------------
# TestGenerateF3HappyPath
# ---------------------------------------------------------------------------


class TestGenerateF3HappyPath:
    def test_exit_code_zero_on_success(self, tmp_path: Path) -> None:
        result = _run_generate_f3(2025, tmp_path / "f3.ics")
        assert result.exit_code == 0, result.output

    def test_ics_file_created(self, tmp_path: Path) -> None:
        output = tmp_path / "f3.ics"
        _run_generate_f3(2025, output)
        assert output.exists()

    def test_ics_file_not_empty(self, tmp_path: Path) -> None:
        output = tmp_path / "f3.ics"
        _run_generate_f3(2025, output)
        assert output.stat().st_size > 0

    def test_ics_contains_vcalendar_header(self, tmp_path: Path) -> None:
        output = tmp_path / "f3.ics"
        _run_generate_f3(2025, output)
        assert "BEGIN:VCALENDAR" in output.read_text()

    def test_output_mentions_event_count(self, tmp_path: Path) -> None:
        result = _run_generate_f3(2025, tmp_path / "f3.ics")
        assert "1 event" in result.output

    def test_output_mentions_year(self, tmp_path: Path) -> None:
        result = _run_generate_f3(2025, tmp_path / "f3.ics")
        assert "2025" in result.output

    def test_output_mentions_source_name(self, tmp_path: Path) -> None:
        result = _run_generate_f3(2025, tmp_path / "f3.ics")
        assert "f1calendar" in result.output

    def test_two_events_in_output(self, tmp_path: Path) -> None:
        result = _run_generate_f3(2025, tmp_path / "f3.ics", _F1CALENDAR_TWO_RACES)
        assert "2 event" in result.output

    def test_empty_season_produces_empty_ics(self, tmp_path: Path) -> None:
        output = tmp_path / "f3.ics"
        result = _run_generate_f3(2025, output, _F1CALENDAR_EMPTY)
        assert result.exit_code == 0
        assert "0 event" in result.output

    def test_refresh_flag_accepted(self, tmp_path: Path) -> None:
        result = _run_generate_f3(2025, tmp_path / "f3.ics", extra_args=["--refresh"])
        assert result.exit_code == 0

    def test_refresh_flag_noted_in_output(self, tmp_path: Path) -> None:
        result = _run_generate_f3(2025, tmp_path / "f3.ics", extra_args=["--refresh"])
        assert "--refresh" in result.output

    def test_sessions_count_in_output(self, tmp_path: Path) -> None:
        result = _run_generate_f3(2025, tmp_path / "f3.ics")
        assert "session" in result.output


# ---------------------------------------------------------------------------
# TestGenerateF3Errors
# ---------------------------------------------------------------------------


class TestGenerateF3Errors:
    def test_http_error_exits_with_code_1(self, tmp_path: Path) -> None:
        import httpx

        request = httpx.Request("GET", "https://example.com")
        response = httpx.Response(404, request=request)
        exc = httpx.HTTPStatusError("HTTP 404", request=request, response=response)

        with patch(
            "motorsport_calendar.providers.formula3.sources.f1calendar.F1CalendarSource.fetch_json",
            new=AsyncMock(side_effect=exc),
        ):
            result = runner.invoke(app, ["generate-f3", "2025", str(tmp_path / "f3.ics")])

        assert result.exit_code == 1

    def test_http_500_exits_with_code_1(self, tmp_path: Path) -> None:
        import httpx

        request = httpx.Request("GET", "https://example.com")
        response = httpx.Response(500, request=request)
        exc = httpx.HTTPStatusError("HTTP 500", request=request, response=response)

        with patch(
            "motorsport_calendar.providers.formula3.sources.f1calendar.F1CalendarSource.fetch_json",
            new=AsyncMock(side_effect=exc),
        ):
            result = runner.invoke(app, ["generate-f3", "2025", str(tmp_path / "f3.ics")])

        assert result.exit_code == 1

    def test_timeout_exits_with_code_1(self, tmp_path: Path) -> None:
        import httpx

        with patch(
            "motorsport_calendar.providers.formula3.sources.f1calendar.F1CalendarSource.fetch_json",
            new=AsyncMock(side_effect=httpx.TimeoutException("timeout")),
        ):
            result = runner.invoke(app, ["generate-f3", "2025", str(tmp_path / "f3.ics")])

        assert result.exit_code == 1

    def test_missing_year_argument_fails(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["generate-f3", str(tmp_path / "f3.ics")])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# TestGenerateF3IcsContent
# ---------------------------------------------------------------------------


class TestGenerateF3IcsContent:
    def test_ics_contains_vevent(self, tmp_path: Path) -> None:
        output = tmp_path / "f3.ics"
        _run_generate_f3(2025, output)
        assert "BEGIN:VEVENT" in output.read_text()

    def test_ics_contains_feature_race(self, tmp_path: Path) -> None:
        output = tmp_path / "f3.ics"
        _run_generate_f3(2025, output)
        assert "Feature Race" in output.read_text()

    def test_ics_contains_qualifying(self, tmp_path: Path) -> None:
        output = tmp_path / "f3.ics"
        _run_generate_f3(2025, output)
        assert "Qualifying" in output.read_text()

    def test_ics_contains_sprint_race(self, tmp_path: Path) -> None:
        output = tmp_path / "f3.ics"
        _run_generate_f3(2025, output)
        assert "Sprint Race" in output.read_text()

    def test_ics_contains_free_practice(self, tmp_path: Path) -> None:
        output = tmp_path / "f3.ics"
        _run_generate_f3(2025, output)
        assert "Free Practice" in output.read_text()

    def test_ics_uid_contains_f3_series_key(self, tmp_path: Path) -> None:
        output = tmp_path / "f3.ics"
        _run_generate_f3(2025, output)
        assert "f1calendar-f3-" in output.read_text()

    def test_four_sessions_for_full_weekend(self, tmp_path: Path) -> None:
        result = _run_generate_f3(2025, tmp_path / "f3.ics")
        assert "4 session" in result.output

    def test_three_sessions_for_partial_weekend(self, tmp_path: Path) -> None:
        # Monaco event has no practice session
        result = _run_generate_f3(2025, tmp_path / "f3.ics", _F1CALENDAR_TWO_RACES)
        assert "7 session" in result.output
