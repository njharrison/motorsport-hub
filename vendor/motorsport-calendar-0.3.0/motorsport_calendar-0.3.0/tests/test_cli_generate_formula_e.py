"""CLI integration tests for `motocal generate-formula-e`."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

from typer.testing import CliRunner

from motorsport_calendar.cli import app

runner = CliRunner()

# ---------------------------------------------------------------------------
# Shared test fixtures
# Formula E uses practice1/practice2/practice3/qualifying/race. Unlike F1
# Academy's triple-header (one Event with race1/race2/race3), Formula E
# splits a double-header weekend into two separate rounds/Events, each
# with its own single "race" — round 1 below is a full first day
# (practice1/practice2/qualifying/race), round 4 mirrors a real second day
# (practice3/qualifying/race only, no practice1/practice2).
# ---------------------------------------------------------------------------

_SAO_PAULO_EVENT: dict[str, Any] = {
    "name": "Sao Paulo ePrix",
    "location": "Sao Paulo",
    "round": 1,
    "slug": "sao-paulo-eprix",
    "localeKey": "sao-paulo-eprix",
    "sessions": {
        "practice1": "2024-12-06T20:00:00Z",
        "practice2": "2024-12-07T10:30:00Z",
        "qualifying": "2024-12-07T12:40:00Z",
        "race": "2024-12-07T17:05:00Z",
    },
}

_MEXICO_EVENT: dict[str, Any] = {
    "name": "Mexico City ePrix",
    "location": "Mexico",
    "round": 2,
    "slug": "mexico-city-eprix",
    "localeKey": "mexico-city-eprix",
    "sessions": {
        "practice1": "2025-01-10T23:00:00Z",
        "practice2": "2025-01-11T13:30:00Z",
        "qualifying": "2025-01-11T15:40:00Z",
        "race": "2025-01-11T20:05:00Z",
    },
}

# Real second-day pattern (Jeddah round 4, 2025 season): no practice1/practice2.
_JEDDAH_DAY2_EVENT: dict[str, Any] = {
    "name": "Jeddah ePrix",
    "location": "Jeddah",
    "round": 4,
    "slug": "jeddah-eprix",
    "localeKey": "jeddah-eprix",
    "sessions": {
        "practice3": "2025-02-14T08:15:00Z",
        "qualifying": "2025-02-14T10:15:00Z",
        "race": "2025-02-14T15:05:00Z",
    },
}

_F1CALENDAR_ONE_RACE: dict[str, Any] = {
    "name": "Formula E",
    "races": [_SAO_PAULO_EVENT],
}

_F1CALENDAR_TWO_RACES: dict[str, Any] = {
    "name": "Formula E",
    "races": [_SAO_PAULO_EVENT, _MEXICO_EVENT],
}

_F1CALENDAR_SECOND_DAY: dict[str, Any] = {
    "name": "Formula E",
    "races": [_JEDDAH_DAY2_EVENT],
}

_F1CALENDAR_EMPTY: dict[str, Any] = {
    "name": "Formula E",
    "races": [],
}


def _run_generate_formula_e(
    year: int,
    output: Path,
    fetch_json_return: Any = _F1CALENDAR_ONE_RACE,
    extra_args: list[str] | None = None,
) -> Any:
    """Invoke `generate-formula-e` with a mocked F1CalendarSource.fetch_json."""
    args = ["generate-formula-e", str(year), str(output)] + (extra_args or [])
    with patch(
        "motorsport_calendar.providers.formula_e.sources.f1calendar.F1CalendarSource.fetch_json",
        new=AsyncMock(return_value=fetch_json_return),
    ):
        return runner.invoke(app, args)


# ---------------------------------------------------------------------------
# TestGenerateFormulaEHappyPath
# ---------------------------------------------------------------------------


class TestGenerateFormulaEHappyPath:
    def test_exit_code_zero_on_success(self, tmp_path: Path) -> None:
        result = _run_generate_formula_e(2025, tmp_path / "fe.ics")
        assert result.exit_code == 0, result.output

    def test_ics_file_created(self, tmp_path: Path) -> None:
        output = tmp_path / "fe.ics"
        _run_generate_formula_e(2025, output)
        assert output.exists()

    def test_ics_file_not_empty(self, tmp_path: Path) -> None:
        output = tmp_path / "fe.ics"
        _run_generate_formula_e(2025, output)
        assert output.stat().st_size > 0

    def test_ics_contains_vcalendar_header(self, tmp_path: Path) -> None:
        output = tmp_path / "fe.ics"
        _run_generate_formula_e(2025, output)
        assert "BEGIN:VCALENDAR" in output.read_text()

    def test_output_mentions_event_count(self, tmp_path: Path) -> None:
        result = _run_generate_formula_e(2025, tmp_path / "fe.ics")
        assert "1 event" in result.output

    def test_output_mentions_year(self, tmp_path: Path) -> None:
        result = _run_generate_formula_e(2025, tmp_path / "fe.ics")
        assert "2025" in result.output

    def test_output_mentions_source_name(self, tmp_path: Path) -> None:
        result = _run_generate_formula_e(2025, tmp_path / "fe.ics")
        assert "f1calendar" in result.output

    def test_output_mentions_formula_e_label(self, tmp_path: Path) -> None:
        result = _run_generate_formula_e(2025, tmp_path / "fe.ics")
        assert "Formula E" in result.output

    def test_two_events_in_output(self, tmp_path: Path) -> None:
        result = _run_generate_formula_e(2025, tmp_path / "fe.ics", _F1CALENDAR_TWO_RACES)
        assert "2 event" in result.output

    def test_empty_season_produces_empty_ics(self, tmp_path: Path) -> None:
        output = tmp_path / "fe.ics"
        result = _run_generate_formula_e(2025, output, _F1CALENDAR_EMPTY)
        assert result.exit_code == 0
        assert "0 event" in result.output

    def test_refresh_flag_accepted(self, tmp_path: Path) -> None:
        result = _run_generate_formula_e(2025, tmp_path / "fe.ics", extra_args=["--refresh"])
        assert result.exit_code == 0

    def test_refresh_flag_noted_in_output(self, tmp_path: Path) -> None:
        result = _run_generate_formula_e(2025, tmp_path / "fe.ics", extra_args=["--refresh"])
        assert "--refresh" in result.output

    def test_sessions_count_in_output(self, tmp_path: Path) -> None:
        result = _run_generate_formula_e(2025, tmp_path / "fe.ics")
        assert "session" in result.output

    def test_four_sessions_for_full_weekend(self, tmp_path: Path) -> None:
        # Sao Paulo has practice1, practice2, qualifying, race
        result = _run_generate_formula_e(2025, tmp_path / "fe.ics")
        assert "4 session" in result.output

    def test_three_sessions_for_second_day(self, tmp_path: Path) -> None:
        # Jeddah round 4 (real second-day pattern) has practice3, qualifying, race
        result = _run_generate_formula_e(2025, tmp_path / "fe.ics", _F1CALENDAR_SECOND_DAY)
        assert "3 session" in result.output


# ---------------------------------------------------------------------------
# TestGenerateFormulaEErrors
# ---------------------------------------------------------------------------


class TestGenerateFormulaEErrors:
    def test_http_error_exits_with_code_1(self, tmp_path: Path) -> None:
        import httpx

        request = httpx.Request("GET", "https://example.com")
        response = httpx.Response(404, request=request)
        exc = httpx.HTTPStatusError("HTTP 404", request=request, response=response)

        with patch(
            "motorsport_calendar.providers.formula_e.sources.f1calendar."
            "F1CalendarSource.fetch_json",
            new=AsyncMock(side_effect=exc),
        ):
            result = runner.invoke(app, ["generate-formula-e", "2025", str(tmp_path / "fe.ics")])

        assert result.exit_code == 1

    def test_http_error_message_mentions_formula_e_source(self, tmp_path: Path) -> None:
        import httpx

        request = httpx.Request("GET", "https://example.com")
        response = httpx.Response(404, request=request)
        exc = httpx.HTTPStatusError("HTTP 404", request=request, response=response)

        with patch(
            "motorsport_calendar.providers.formula_e.sources.f1calendar."
            "F1CalendarSource.fetch_json",
            new=AsyncMock(side_effect=exc),
        ):
            result = runner.invoke(app, ["generate-formula-e", "2025", str(tmp_path / "fe.ics")])

        assert "Formula E source error" in result.output

    def test_http_500_exits_with_code_1(self, tmp_path: Path) -> None:
        import httpx

        request = httpx.Request("GET", "https://example.com")
        response = httpx.Response(500, request=request)
        exc = httpx.HTTPStatusError("HTTP 500", request=request, response=response)

        with patch(
            "motorsport_calendar.providers.formula_e.sources.f1calendar."
            "F1CalendarSource.fetch_json",
            new=AsyncMock(side_effect=exc),
        ):
            result = runner.invoke(app, ["generate-formula-e", "2025", str(tmp_path / "fe.ics")])

        assert result.exit_code == 1

    def test_timeout_exits_with_code_1(self, tmp_path: Path) -> None:
        import httpx

        with patch(
            "motorsport_calendar.providers.formula_e.sources.f1calendar."
            "F1CalendarSource.fetch_json",
            new=AsyncMock(side_effect=httpx.TimeoutException("timeout")),
        ):
            result = runner.invoke(app, ["generate-formula-e", "2025", str(tmp_path / "fe.ics")])

        assert result.exit_code == 1

    def test_missing_year_argument_fails(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["generate-formula-e", str(tmp_path / "fe.ics")])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# TestGenerateFormulaEIcsContent
# ---------------------------------------------------------------------------


class TestGenerateFormulaEIcsContent:
    def test_ics_contains_vevent(self, tmp_path: Path) -> None:
        output = tmp_path / "fe.ics"
        _run_generate_formula_e(2025, output)
        assert "BEGIN:VEVENT" in output.read_text()

    def test_ics_contains_race(self, tmp_path: Path) -> None:
        output = tmp_path / "fe.ics"
        _run_generate_formula_e(2025, output)
        assert "Race" in output.read_text()

    def test_ics_contains_qualifying(self, tmp_path: Path) -> None:
        output = tmp_path / "fe.ics"
        _run_generate_formula_e(2025, output)
        assert "Qualifying" in output.read_text()

    def test_ics_contains_free_practice_1(self, tmp_path: Path) -> None:
        output = tmp_path / "fe.ics"
        _run_generate_formula_e(2025, output)
        assert "Free Practice 1" in output.read_text()

    def test_ics_contains_free_practice_3_on_second_day(self, tmp_path: Path) -> None:
        output = tmp_path / "fe.ics"
        _run_generate_formula_e(2025, output, _F1CALENDAR_SECOND_DAY)
        assert "Free Practice 3" in output.read_text()

    def test_ics_uid_contains_series_key(self, tmp_path: Path) -> None:
        output = tmp_path / "fe.ics"
        _run_generate_formula_e(2025, output)
        assert "f1calendar-fe-" in output.read_text()

    def test_no_duplicate_uids(self, tmp_path: Path) -> None:
        """RFC 5545: UIDs must be unique within a calendar."""
        output = tmp_path / "fe.ics"
        _run_generate_formula_e(2025, output, _F1CALENDAR_TWO_RACES)
        content = output.read_text()
        uids = [line for line in content.splitlines() if line.startswith("UID:")]
        assert len(uids) == len(set(uids)), "Duplicate UIDs detected in ICS output"

    def test_two_events_produce_eight_vevents(self, tmp_path: Path) -> None:
        # 2 events x 4 sessions each (practice1 + practice2 + qualifying + race)
        output = tmp_path / "fe.ics"
        _run_generate_formula_e(2025, output, _F1CALENDAR_TWO_RACES)
        assert output.read_text().count("BEGIN:VEVENT") == 8
