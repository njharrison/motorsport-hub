"""CLI integration tests for `motocal generate-gtwc-america`.

SroScraperSource.fetch_html is mocked at the URL level (calendar page vs
per-round event page), using the real captured fixtures in
tests/fixtures/real/ — same fixtures used by test_sro_timetable_base.py.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

from typer.testing import CliRunner

from motorsport_calendar.cli import app
from tests.conftest import load_real_fixture

runner = CliRunner()


_CALENDAR_SEVEN_ROUNDS = load_real_fixture("gtwc_america_calendar.html")
_EVENT_COTA = load_real_fixture("gtwc_america_event_cota.html")
_CALENDAR_EMPTY = "<html><body>no rounds this year</body></html>"

_PATCH_TARGET = (
    "motorsport_calendar.providers.gtwc_america.sources.sro_scraper.SroScraperSource.fetch_html"
)


def _fallback_to_cota() -> Any:
    async def _fake_fetch_html(url: str) -> str:
        if "/calendar" in url:
            return _CALENDAR_SEVEN_ROUNDS
        return _EVENT_COTA

    return _fake_fetch_html


def _empty_calendar() -> Any:
    async def _fake_fetch_html(url: str) -> str:
        return _CALENDAR_EMPTY

    return _fake_fetch_html


def _run_generate_gtwc_america(
    year: int,
    output: Path,
    fetch_html_effect: Any,
    extra_args: list[str] | None = None,
) -> Any:
    args = ["generate-gtwc-america", str(year), str(output)] + (extra_args or [])
    with patch(_PATCH_TARGET, new=AsyncMock(side_effect=fetch_html_effect)):
        return runner.invoke(app, args)


class TestGenerateGtwcAmericaHappyPath:
    def test_exit_code_zero_on_success(self, tmp_path: Path) -> None:
        result = _run_generate_gtwc_america(2071, tmp_path / "gtwca.ics", _fallback_to_cota())
        assert result.exit_code == 0, result.output

    def test_ics_file_created(self, tmp_path: Path) -> None:
        output = tmp_path / "gtwca.ics"
        _run_generate_gtwc_america(2072, output, _fallback_to_cota())
        assert output.exists()

    def test_output_mentions_seven_events(self, tmp_path: Path) -> None:
        result = _run_generate_gtwc_america(2073, tmp_path / "gtwca.ics", _fallback_to_cota())
        assert "7 event" in result.output

    def test_output_mentions_gtwc_america_label(self, tmp_path: Path) -> None:
        result = _run_generate_gtwc_america(2074, tmp_path / "gtwca.ics", _fallback_to_cota())
        assert "GT World Challenge America" in result.output

    def test_empty_calendar_produces_empty_ics(self, tmp_path: Path) -> None:
        output = tmp_path / "gtwca.ics"
        result = _run_generate_gtwc_america(2075, output, _empty_calendar())
        assert result.exit_code == 0
        assert "0 event" in result.output

    def test_refresh_flag_accepted(self, tmp_path: Path) -> None:
        result = _run_generate_gtwc_america(
            2076, tmp_path / "gtwca.ics", _fallback_to_cota(), extra_args=["--refresh"]
        )
        assert result.exit_code == 0

    def test_thirty_five_sessions_across_seven_rounds(self, tmp_path: Path) -> None:
        # 7 rounds x 5 sessions each (COTA fixture reused for every round)
        result = _run_generate_gtwc_america(2077, tmp_path / "gtwca.ics", _fallback_to_cota())
        assert "35 session" in result.output


class TestGenerateGtwcAmericaErrors:
    def test_http_error_exits_with_code_1(self, tmp_path: Path) -> None:
        import httpx

        request = httpx.Request("GET", "https://example.com")
        response = httpx.Response(503, request=request)
        exc = httpx.HTTPStatusError("HTTP 503", request=request, response=response)

        with patch(_PATCH_TARGET, new=AsyncMock(side_effect=exc)):
            result = runner.invoke(
                app, ["generate-gtwc-america", "2078", str(tmp_path / "gtwca.ics")]
            )

        assert result.exit_code == 1
        assert "GT World Challenge America source error" in result.output

    def test_timeout_exits_with_code_1(self, tmp_path: Path) -> None:
        import httpx

        with patch(_PATCH_TARGET, new=AsyncMock(side_effect=httpx.TimeoutException("timeout"))):
            result = runner.invoke(
                app, ["generate-gtwc-america", "2079", str(tmp_path / "gtwca.ics")]
            )

        assert result.exit_code == 1

    def test_missing_year_argument_fails(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["generate-gtwc-america", str(tmp_path / "gtwca.ics")])
        assert result.exit_code != 0


class TestGenerateGtwcAmericaIcsContent:
    def test_ics_contains_vevent(self, tmp_path: Path) -> None:
        output = tmp_path / "gtwca.ics"
        _run_generate_gtwc_america(2080, output, _fallback_to_cota())
        assert "BEGIN:VEVENT" in output.read_text()

    def test_ics_uid_contains_series_key(self, tmp_path: Path) -> None:
        output = tmp_path / "gtwca.ics"
        _run_generate_gtwc_america(2081, output, _fallback_to_cota())
        assert "gtwc-america-2081-" in output.read_text()

    def test_no_duplicate_uids(self, tmp_path: Path) -> None:
        import re

        output = tmp_path / "gtwca.ics"
        _run_generate_gtwc_america(2082, output, _fallback_to_cota())
        unfolded = re.sub(r"\r?\n ", "", output.read_text())
        uids = re.findall(r"^UID:(.+)$", unfolded, re.MULTILINE)
        assert len(uids) == len(set(uids)), "Duplicate UIDs detected in ICS output"

    def test_five_vevents_per_round_thirty_five_total(self, tmp_path: Path) -> None:
        output = tmp_path / "gtwca.ics"
        _run_generate_gtwc_america(2083, output, _fallback_to_cota())
        assert output.read_text().count("BEGIN:VEVENT") == 35
