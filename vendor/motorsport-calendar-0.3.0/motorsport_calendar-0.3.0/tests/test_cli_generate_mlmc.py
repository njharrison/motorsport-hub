"""CLI integration tests for `motocal generate-mlmc`.

AcoScraperSource.fetch_html is mocked at the URL level (season page vs
race detail page). Season page fixture reuses the ELMS snippet structure
(same CMS, only the domain differs at runtime) pointed at the real MLMC
Barcelona race fixture — see test_aco_sports_event_base.py for the
dedicated real-data session/merge/UID tests; this file only locks down
CLI-level behaviour (exit codes, output text, ICS content).
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
    async def _fake_fetch_html(url: str) -> str:
        for marker, html in html_by_marker:
            if marker in url:
                return html
        return "<html><body>no data</body></html>"

    return _fake_fetch_html


# Real MLMC season page links to a "barcelona-round-2026" race — reuse the
# ELMS season snippet's markup shape but swap in a Barcelona-round link so
# _extract_race_urls finds exactly one round, matching the fixture below.
_SEASON_ONE_RACE = (
    '<!DOCTYPE html><html><body><a href="/en/race/barcelona-round-2026">'
    "Barcelona Round</a></body></html>"
)
_RACE_BARCELONA = load_real_fixture("mlmc_race_barcelona.html")
_SEASON_EMPTY = "<html><body>no races this year</body></html>"


def _run_generate_mlmc(
    year: int,
    output: Path,
    fetch_html_effect: Any = None,
    extra_args: list[str] | None = None,
) -> Any:
    effect = fetch_html_effect or _fetch_html_side_effect(
        ("season", _SEASON_ONE_RACE), ("race", _RACE_BARCELONA)
    )
    args = ["generate-mlmc", str(year), str(output)] + (extra_args or [])
    with patch(
        "motorsport_calendar.providers.mlmc.sources.aco_scraper.AcoScraperSource.fetch_html",
        new=AsyncMock(side_effect=effect),
    ):
        return runner.invoke(app, args)


class TestGenerateMlmcHappyPath:
    def test_exit_code_zero_on_success(self, tmp_path: Path) -> None:
        result = _run_generate_mlmc(2071, tmp_path / "mlmc.ics")
        assert result.exit_code == 0, result.output

    def test_ics_file_created(self, tmp_path: Path) -> None:
        output = tmp_path / "mlmc.ics"
        _run_generate_mlmc(2072, output)
        assert output.exists()

    def test_ics_contains_vcalendar_header(self, tmp_path: Path) -> None:
        output = tmp_path / "mlmc.ics"
        _run_generate_mlmc(2073, output)
        assert "BEGIN:VCALENDAR" in output.read_text()

    def test_output_mentions_event_count(self, tmp_path: Path) -> None:
        result = _run_generate_mlmc(2074, tmp_path / "mlmc.ics")
        assert "1 event" in result.output

    def test_output_mentions_mlmc_label(self, tmp_path: Path) -> None:
        result = _run_generate_mlmc(2075, tmp_path / "mlmc.ics")
        assert "MLMC" in result.output

    def test_output_mentions_source_name(self, tmp_path: Path) -> None:
        result = _run_generate_mlmc(2076, tmp_path / "mlmc.ics")
        assert "aco_scraper" in result.output

    def test_empty_season_produces_empty_ics(self, tmp_path: Path) -> None:
        output = tmp_path / "mlmc.ics"
        result = _run_generate_mlmc(
            2077, output, _fetch_html_side_effect(("season", _SEASON_EMPTY))
        )
        assert result.exit_code == 0
        assert "0 event" in result.output

    def test_refresh_flag_accepted(self, tmp_path: Path) -> None:
        result = _run_generate_mlmc(2078, tmp_path / "mlmc.ics", extra_args=["--refresh"])
        assert result.exit_code == 0


class TestGenerateMlmcErrors:
    def test_http_error_exits_with_code_1(self, tmp_path: Path) -> None:
        import httpx

        request = httpx.Request("GET", "https://example.com")
        response = httpx.Response(503, request=request)
        exc = httpx.HTTPStatusError("HTTP 503", request=request, response=response)

        with patch(
            "motorsport_calendar.providers.mlmc.sources.aco_scraper.AcoScraperSource.fetch_html",
            new=AsyncMock(side_effect=exc),
        ):
            result = runner.invoke(app, ["generate-mlmc", "2079", str(tmp_path / "mlmc.ics")])

        assert result.exit_code == 1

    def test_http_error_message_mentions_mlmc_source(self, tmp_path: Path) -> None:
        import httpx

        request = httpx.Request("GET", "https://example.com")
        response = httpx.Response(503, request=request)
        exc = httpx.HTTPStatusError("HTTP 503", request=request, response=response)

        with patch(
            "motorsport_calendar.providers.mlmc.sources.aco_scraper.AcoScraperSource.fetch_html",
            new=AsyncMock(side_effect=exc),
        ):
            result = runner.invoke(app, ["generate-mlmc", "2080", str(tmp_path / "mlmc.ics")])

        assert "MLMC source error" in result.output

    def test_timeout_exits_with_code_1(self, tmp_path: Path) -> None:
        import httpx

        with patch(
            "motorsport_calendar.providers.mlmc.sources.aco_scraper.AcoScraperSource.fetch_html",
            new=AsyncMock(side_effect=httpx.TimeoutException("timeout")),
        ):
            result = runner.invoke(app, ["generate-mlmc", "2081", str(tmp_path / "mlmc.ics")])

        assert result.exit_code == 1

    def test_missing_year_argument_fails(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["generate-mlmc", str(tmp_path / "mlmc.ics")])
        assert result.exit_code != 0


class TestGenerateMlmcIcsContent:
    def test_ics_contains_vevent(self, tmp_path: Path) -> None:
        output = tmp_path / "mlmc.ics"
        _run_generate_mlmc(2082, output)
        assert "BEGIN:VEVENT" in output.read_text()

    def test_ics_contains_race(self, tmp_path: Path) -> None:
        output = tmp_path / "mlmc.ics"
        _run_generate_mlmc(2083, output)
        assert "Race" in output.read_text()

    def test_ics_uid_contains_series_key(self, tmp_path: Path) -> None:
        output = tmp_path / "mlmc.ics"
        _run_generate_mlmc(2084, output)
        assert "mlmc-2084-" in output.read_text()

    def test_no_duplicate_uids(self, tmp_path: Path) -> None:
        output = tmp_path / "mlmc.ics"
        _run_generate_mlmc(2085, output)
        content = output.read_text()
        uids = [line for line in content.splitlines() if line.startswith("UID:")]
        assert len(uids) == len(set(uids)), "Duplicate UIDs detected in ICS output"
