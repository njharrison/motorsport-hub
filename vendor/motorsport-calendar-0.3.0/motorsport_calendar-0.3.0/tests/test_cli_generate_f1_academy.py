"""CLI integration tests for `motocal generate-f1-academy`."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

from typer.testing import CliRunner

from motorsport_calendar.cli import app

runner = CliRunner()

# ---------------------------------------------------------------------------
# Shared test fixtures
# F1 Academy uses fp1/fp2/qualifying1/qualifying2/race1/race2/race3.
# A 2025-style event has no qualifying2.
# ---------------------------------------------------------------------------

_JEDDAH_EVENT: dict[str, Any] = {
    "name": "Jeddah",
    "location": "Jeddah",
    "round": 1,
    "slug": "jeddah",
    "localeKey": "jeddah",
    "sessions": {
        "fp1": "2025-03-20T10:00:00Z",
        "fp2": "2025-03-20T14:00:00Z",
        "qualifying1": "2025-03-21T10:00:00Z",
        "race1": "2025-03-21T15:00:00Z",
        "race2": "2025-03-22T10:00:00Z",
        "race3": "2025-03-22T14:00:00Z",
    },
}

# 2023-style event: has qualifying2
_SPIELBERG_EVENT_2023: dict[str, Any] = {
    "name": "Spielberg",
    "location": "Spielberg",
    "round": 1,
    "slug": "spielberg",
    "localeKey": "spielberg",
    "sessions": {
        "fp1": "2023-06-29T10:00:00Z",
        "fp2": "2023-06-29T14:00:00Z",
        "qualifying1": "2023-06-30T10:00:00Z",
        "qualifying2": "2023-06-30T14:00:00Z",
        "race1": "2023-07-01T09:00:00Z",
        "race2": "2023-07-01T12:00:00Z",
        "race3": "2023-07-01T15:00:00Z",
    },
}

_MIAMI_EVENT: dict[str, Any] = {
    "name": "Miami",
    "location": "USA",
    "round": 2,
    "slug": "miami",
    "localeKey": "miami",
    "sessions": {
        "fp1": "2025-05-01T10:00:00Z",
        "qualifying1": "2025-05-02T10:00:00Z",
        "race1": "2025-05-02T15:00:00Z",
        "race2": "2025-05-03T10:00:00Z",
        "race3": "2025-05-03T14:00:00Z",
    },
}

_F1CALENDAR_ONE_RACE: dict[str, Any] = {
    "name": "F1 Academy",
    "races": [_JEDDAH_EVENT],
}

_F1CALENDAR_TWO_RACES: dict[str, Any] = {
    "name": "F1 Academy",
    "races": [_JEDDAH_EVENT, _MIAMI_EVENT],
}

_F1CALENDAR_WITH_Q2: dict[str, Any] = {
    "name": "F1 Academy",
    "races": [_SPIELBERG_EVENT_2023],
}

_F1CALENDAR_EMPTY: dict[str, Any] = {
    "name": "F1 Academy",
    "races": [],
}


def _run_generate_f1_academy(
    year: int,
    output: Path,
    fetch_json_return: Any = _F1CALENDAR_ONE_RACE,
    extra_args: list[str] | None = None,
) -> Any:
    """Invoke `generate-f1-academy` with a mocked F1CalendarSource.fetch_json."""
    args = ["generate-f1-academy", str(year), str(output)] + (extra_args or [])
    with patch(
        "motorsport_calendar.providers.f1_academy.sources.f1calendar.F1CalendarSource.fetch_json",
        new=AsyncMock(return_value=fetch_json_return),
    ):
        return runner.invoke(app, args)


# ---------------------------------------------------------------------------
# TestGenerateF1AcademyHappyPath
# ---------------------------------------------------------------------------


class TestGenerateF1AcademyHappyPath:
    def test_exit_code_zero_on_success(self, tmp_path: Path) -> None:
        result = _run_generate_f1_academy(2025, tmp_path / "f1a.ics")
        assert result.exit_code == 0, result.output

    def test_ics_file_created(self, tmp_path: Path) -> None:
        output = tmp_path / "f1a.ics"
        _run_generate_f1_academy(2025, output)
        assert output.exists()

    def test_ics_file_not_empty(self, tmp_path: Path) -> None:
        output = tmp_path / "f1a.ics"
        _run_generate_f1_academy(2025, output)
        assert output.stat().st_size > 0

    def test_ics_contains_vcalendar_header(self, tmp_path: Path) -> None:
        output = tmp_path / "f1a.ics"
        _run_generate_f1_academy(2025, output)
        assert "BEGIN:VCALENDAR" in output.read_text()

    def test_output_mentions_event_count(self, tmp_path: Path) -> None:
        result = _run_generate_f1_academy(2025, tmp_path / "f1a.ics")
        assert "1 event" in result.output

    def test_output_mentions_year(self, tmp_path: Path) -> None:
        result = _run_generate_f1_academy(2025, tmp_path / "f1a.ics")
        assert "2025" in result.output

    def test_output_mentions_source_name(self, tmp_path: Path) -> None:
        result = _run_generate_f1_academy(2025, tmp_path / "f1a.ics")
        assert "f1calendar" in result.output

    def test_two_events_in_output(self, tmp_path: Path) -> None:
        result = _run_generate_f1_academy(2025, tmp_path / "f1a.ics", _F1CALENDAR_TWO_RACES)
        assert "2 event" in result.output

    def test_empty_season_produces_empty_ics(self, tmp_path: Path) -> None:
        output = tmp_path / "f1a.ics"
        result = _run_generate_f1_academy(2025, output, _F1CALENDAR_EMPTY)
        assert result.exit_code == 0
        assert "0 event" in result.output

    def test_refresh_flag_accepted(self, tmp_path: Path) -> None:
        result = _run_generate_f1_academy(2025, tmp_path / "f1a.ics", extra_args=["--refresh"])
        assert result.exit_code == 0

    def test_refresh_flag_noted_in_output(self, tmp_path: Path) -> None:
        result = _run_generate_f1_academy(2025, tmp_path / "f1a.ics", extra_args=["--refresh"])
        assert "--refresh" in result.output

    def test_sessions_count_in_output(self, tmp_path: Path) -> None:
        result = _run_generate_f1_academy(2025, tmp_path / "f1a.ics")
        assert "session" in result.output


# ---------------------------------------------------------------------------
# TestGenerateF1AcademyErrors
# ---------------------------------------------------------------------------


class TestGenerateF1AcademyErrors:
    def test_http_error_exits_with_code_1(self, tmp_path: Path) -> None:
        import httpx

        request = httpx.Request("GET", "https://example.com")
        response = httpx.Response(404, request=request)
        exc = httpx.HTTPStatusError("HTTP 404", request=request, response=response)

        with patch(
            "motorsport_calendar.providers.f1_academy.sources.f1calendar.F1CalendarSource.fetch_json",
            new=AsyncMock(side_effect=exc),
        ):
            result = runner.invoke(app, ["generate-f1-academy", "2025", str(tmp_path / "f1a.ics")])

        assert result.exit_code == 1

    def test_http_500_exits_with_code_1(self, tmp_path: Path) -> None:
        import httpx

        request = httpx.Request("GET", "https://example.com")
        response = httpx.Response(500, request=request)
        exc = httpx.HTTPStatusError("HTTP 500", request=request, response=response)

        with patch(
            "motorsport_calendar.providers.f1_academy.sources.f1calendar.F1CalendarSource.fetch_json",
            new=AsyncMock(side_effect=exc),
        ):
            result = runner.invoke(app, ["generate-f1-academy", "2025", str(tmp_path / "f1a.ics")])

        assert result.exit_code == 1

    def test_timeout_exits_with_code_1(self, tmp_path: Path) -> None:
        import httpx

        with patch(
            "motorsport_calendar.providers.f1_academy.sources.f1calendar.F1CalendarSource.fetch_json",
            new=AsyncMock(side_effect=httpx.TimeoutException("timeout")),
        ):
            result = runner.invoke(app, ["generate-f1-academy", "2025", str(tmp_path / "f1a.ics")])

        assert result.exit_code == 1

    def test_missing_year_argument_fails(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["generate-f1-academy", str(tmp_path / "f1a.ics")])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# TestGenerateF1AcademyIcsContent
# ---------------------------------------------------------------------------


class TestGenerateF1AcademyIcsContent:
    def test_ics_contains_vevent(self, tmp_path: Path) -> None:
        output = tmp_path / "f1a.ics"
        _run_generate_f1_academy(2025, output)
        assert "BEGIN:VEVENT" in output.read_text()

    def test_ics_contains_race_3(self, tmp_path: Path) -> None:
        output = tmp_path / "f1a.ics"
        _run_generate_f1_academy(2025, output)
        assert "Race 3" in output.read_text()

    def test_ics_contains_race_1(self, tmp_path: Path) -> None:
        output = tmp_path / "f1a.ics"
        _run_generate_f1_academy(2025, output)
        assert "Race 1" in output.read_text()

    def test_ics_contains_race_2(self, tmp_path: Path) -> None:
        output = tmp_path / "f1a.ics"
        _run_generate_f1_academy(2025, output)
        assert "Race 2" in output.read_text()

    def test_ics_contains_free_practice(self, tmp_path: Path) -> None:
        output = tmp_path / "f1a.ics"
        _run_generate_f1_academy(2025, output)
        content = output.read_text()
        assert "Free Practice" in content

    def test_ics_contains_qualifying(self, tmp_path: Path) -> None:
        output = tmp_path / "f1a.ics"
        _run_generate_f1_academy(2025, output)
        assert "Qualifying" in output.read_text()

    def test_ics_uid_contains_series_key(self, tmp_path: Path) -> None:
        output = tmp_path / "f1a.ics"
        _run_generate_f1_academy(2025, output)
        assert "f1calendar-f1-academy-" in output.read_text()

    def test_no_duplicate_uids(self, tmp_path: Path) -> None:
        """RFC 5545: UIDs must be unique within a calendar."""
        output = tmp_path / "f1a.ics"
        _run_generate_f1_academy(2025, output)
        content = output.read_text()
        uids = [line for line in content.splitlines() if line.startswith("UID:")]
        assert len(uids) == len(set(uids)), "Duplicate UIDs detected in ICS output"

    def test_six_sessions_for_full_weekend(self, tmp_path: Path) -> None:
        # Jeddah has fp1, fp2, qualifying1, race1, race2, race3
        result = _run_generate_f1_academy(2025, tmp_path / "f1a.ics")
        assert "6 session" in result.output

    def test_seven_sessions_with_qualifying2(self, tmp_path: Path) -> None:
        # Spielberg 2023 has fp1, fp2, qualifying1, qualifying2, race1, race2, race3
        result = _run_generate_f1_academy(2023, tmp_path / "f1a.ics", _F1CALENDAR_WITH_Q2)
        assert "7 session" in result.output
