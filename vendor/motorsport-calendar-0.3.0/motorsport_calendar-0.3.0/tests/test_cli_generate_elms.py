"""CLI integration tests for `motocal generate-elms`.

AcoScraperSource.fetch_html is mocked at the URL level (season page vs
race detail page), using the real captured fixtures in tests/fixtures/real/
— same real Barcelona round used by test_aco_sports_event_base.py.

Different scenarios use different years so each gets its own HttpCache key
(the CLI constructs a real, disk-backed HttpCache — same convention already
used by the other generate-* CLI test files to avoid cross-test cache
collisions).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

from typer.testing import CliRunner

from motorsport_calendar.cli import app
from tests.conftest import load_real_fixture

runner = CliRunner()


def _fetch_html_side_effect(*html_by_marker: tuple[str, str]) -> Any:
    """Return HTML content based on a marker substring found in the URL."""

    async def _fake_fetch_html(url: str) -> str:
        for marker, html in html_by_marker:
            if marker in url:
                return html
        return "<html><body>no data</body></html>"

    return _fake_fetch_html


_SEASON_ONE_RACE = load_real_fixture("elms_season_snippet.html")
_RACE_BARCELONA = load_real_fixture("elms_race_barcelona.html")
_SEASON_EMPTY = "<html><body>no races this year</body></html>"


def _run_generate_elms(
    year: int,
    output: Path,
    fetch_html_effect: Any = None,
    extra_args: list[str] | None = None,
) -> Any:
    effect = fetch_html_effect or _fetch_html_side_effect(
        ("season", _SEASON_ONE_RACE), ("race", _RACE_BARCELONA)
    )
    args = ["generate-elms", str(year), str(output)] + (extra_args or [])
    with patch(
        "motorsport_calendar.providers.elms.sources.aco_scraper.AcoScraperSource.fetch_html",
        new=AsyncMock(side_effect=effect),
    ):
        return runner.invoke(app, args)


class TestGenerateElmsHappyPath:
    def test_exit_code_zero_on_success(self, tmp_path: Path) -> None:
        result = _run_generate_elms(2051, tmp_path / "elms.ics")
        assert result.exit_code == 0, result.output

    def test_ics_file_created(self, tmp_path: Path) -> None:
        output = tmp_path / "elms.ics"
        _run_generate_elms(2052, output)
        assert output.exists()

    def test_ics_contains_vcalendar_header(self, tmp_path: Path) -> None:
        output = tmp_path / "elms.ics"
        _run_generate_elms(2053, output)
        assert "BEGIN:VCALENDAR" in output.read_text()

    def test_output_mentions_event_count(self, tmp_path: Path) -> None:
        result = _run_generate_elms(2054, tmp_path / "elms.ics")
        assert "1 event" in result.output

    def test_output_mentions_elms_label(self, tmp_path: Path) -> None:
        result = _run_generate_elms(2055, tmp_path / "elms.ics")
        assert "ELMS" in result.output

    def test_output_mentions_source_name(self, tmp_path: Path) -> None:
        result = _run_generate_elms(2056, tmp_path / "elms.ics")
        assert "aco_scraper" in result.output

    def test_empty_season_produces_empty_ics(self, tmp_path: Path) -> None:
        output = tmp_path / "elms.ics"
        result = _run_generate_elms(
            2057, output, _fetch_html_side_effect(("season", _SEASON_EMPTY))
        )
        assert result.exit_code == 0
        assert "0 event" in result.output

    def test_refresh_flag_accepted(self, tmp_path: Path) -> None:
        result = _run_generate_elms(2058, tmp_path / "elms.ics", extra_args=["--refresh"])
        assert result.exit_code == 0

    def test_five_sessions_in_output(self, tmp_path: Path) -> None:
        result = _run_generate_elms(2059, tmp_path / "elms.ics")
        assert "5 session" in result.output


class TestGenerateElmsErrors:
    def test_http_error_exits_with_code_1(self, tmp_path: Path) -> None:
        import httpx

        request = httpx.Request("GET", "https://example.com")
        response = httpx.Response(503, request=request)
        exc = httpx.HTTPStatusError("HTTP 503", request=request, response=response)

        with patch(
            "motorsport_calendar.providers.elms.sources.aco_scraper.AcoScraperSource.fetch_html",
            new=AsyncMock(side_effect=exc),
        ):
            result = runner.invoke(app, ["generate-elms", "2060", str(tmp_path / "elms.ics")])

        assert result.exit_code == 1

    def test_http_error_message_mentions_elms_source(self, tmp_path: Path) -> None:
        import httpx

        request = httpx.Request("GET", "https://example.com")
        response = httpx.Response(503, request=request)
        exc = httpx.HTTPStatusError("HTTP 503", request=request, response=response)

        with patch(
            "motorsport_calendar.providers.elms.sources.aco_scraper.AcoScraperSource.fetch_html",
            new=AsyncMock(side_effect=exc),
        ):
            result = runner.invoke(app, ["generate-elms", "2061", str(tmp_path / "elms.ics")])

        assert "ELMS source error" in result.output

    def test_timeout_exits_with_code_1(self, tmp_path: Path) -> None:
        import httpx

        with patch(
            "motorsport_calendar.providers.elms.sources.aco_scraper.AcoScraperSource.fetch_html",
            new=AsyncMock(side_effect=httpx.TimeoutException("timeout")),
        ):
            result = runner.invoke(app, ["generate-elms", "2062", str(tmp_path / "elms.ics")])

        assert result.exit_code == 1

    def test_missing_year_argument_fails(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["generate-elms", str(tmp_path / "elms.ics")])
        assert result.exit_code != 0


class TestGenerateElmsIcsContent:
    def test_ics_contains_vevent(self, tmp_path: Path) -> None:
        output = tmp_path / "elms.ics"
        _run_generate_elms(2063, output)
        assert "BEGIN:VEVENT" in output.read_text()

    def test_ics_contains_race(self, tmp_path: Path) -> None:
        output = tmp_path / "elms.ics"
        _run_generate_elms(2064, output)
        assert "Race" in output.read_text()

    def test_ics_contains_qualifying(self, tmp_path: Path) -> None:
        output = tmp_path / "elms.ics"
        _run_generate_elms(2065, output)
        assert "Qualifying" in output.read_text()

    def test_ics_uid_contains_series_key(self, tmp_path: Path) -> None:
        output = tmp_path / "elms.ics"
        _run_generate_elms(2066, output)
        assert "elms-2066-" in output.read_text()

    def test_no_duplicate_uids(self, tmp_path: Path) -> None:
        """RFC 5545: UIDs must be unique within a calendar."""
        output = tmp_path / "elms.ics"
        _run_generate_elms(2067, output)
        content = output.read_text()
        uids = [line for line in content.splitlines() if line.startswith("UID:")]
        assert len(uids) == len(set(uids)), "Duplicate UIDs detected in ICS output"

    def test_five_vevents_for_one_round(self, tmp_path: Path) -> None:
        # 1 round x 5 sessions (FP1, FP2, Test, merged Qualifying, Race)
        output = tmp_path / "elms.ics"
        _run_generate_elms(2068, output)
        assert output.read_text().count("BEGIN:VEVENT") == 5
