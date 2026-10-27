"""CLI integration tests for `motocal generate-igtc`.

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


_CALENDAR_FIVE_ROUNDS = load_real_fixture("igtc_calendar.html")
_EVENT_BATHURST = load_real_fixture("igtc_event_bathurst.html")
_CALENDAR_EMPTY = "<html><body>no rounds this year</body></html>"

_PATCH_TARGET = "motorsport_calendar.providers.igtc.sources.sro_scraper.SroScraperSource.fetch_html"


def _fallback_to_bathurst() -> Any:
    async def _fake_fetch_html(url: str) -> str:
        if "/calendar" in url:
            return _CALENDAR_FIVE_ROUNDS
        return _EVENT_BATHURST

    return _fake_fetch_html


def _empty_calendar() -> Any:
    async def _fake_fetch_html(url: str) -> str:
        return _CALENDAR_EMPTY

    return _fake_fetch_html


def _run_generate_igtc(
    year: int,
    output: Path,
    fetch_html_effect: Any,
    extra_args: list[str] | None = None,
) -> Any:
    args = ["generate-igtc", str(year), str(output)] + (extra_args or [])
    with patch(_PATCH_TARGET, new=AsyncMock(side_effect=fetch_html_effect)):
        return runner.invoke(app, args)


class TestGenerateIgtcHappyPath:
    def test_exit_code_zero_on_success(self, tmp_path: Path) -> None:
        result = _run_generate_igtc(2035, tmp_path / "igtc.ics", _fallback_to_bathurst())
        assert result.exit_code == 0, result.output

    def test_ics_file_created(self, tmp_path: Path) -> None:
        output = tmp_path / "igtc.ics"
        _run_generate_igtc(2036, output, _fallback_to_bathurst())
        assert output.exists()

    def test_output_mentions_five_events(self, tmp_path: Path) -> None:
        result = _run_generate_igtc(2037, tmp_path / "igtc.ics", _fallback_to_bathurst())
        assert "5 event" in result.output

    def test_output_mentions_igtc_label(self, tmp_path: Path) -> None:
        result = _run_generate_igtc(2038, tmp_path / "igtc.ics", _fallback_to_bathurst())
        assert "IGTC" in result.output

    def test_empty_calendar_produces_empty_ics(self, tmp_path: Path) -> None:
        output = tmp_path / "igtc.ics"
        result = _run_generate_igtc(2039, output, _empty_calendar())
        assert result.exit_code == 0
        assert "0 event" in result.output

    def test_refresh_flag_accepted(self, tmp_path: Path) -> None:
        result = _run_generate_igtc(
            2040, tmp_path / "igtc.ics", _fallback_to_bathurst(), extra_args=["--refresh"]
        )
        assert result.exit_code == 0

    def test_twenty_five_sessions_across_five_rounds(self, tmp_path: Path) -> None:
        # 5 rounds x 5 sessions each (Bathurst fixture reused for every round)
        result = _run_generate_igtc(2041, tmp_path / "igtc.ics", _fallback_to_bathurst())
        assert "25 session" in result.output


class TestGenerateIgtcErrors:
    def test_http_error_exits_with_code_1(self, tmp_path: Path) -> None:
        import httpx

        request = httpx.Request("GET", "https://example.com")
        response = httpx.Response(503, request=request)
        exc = httpx.HTTPStatusError("HTTP 503", request=request, response=response)

        with patch(_PATCH_TARGET, new=AsyncMock(side_effect=exc)):
            result = runner.invoke(app, ["generate-igtc", "2042", str(tmp_path / "igtc.ics")])

        assert result.exit_code == 1
        assert "IGTC source error" in result.output

    def test_timeout_exits_with_code_1(self, tmp_path: Path) -> None:
        import httpx

        with patch(_PATCH_TARGET, new=AsyncMock(side_effect=httpx.TimeoutException("timeout"))):
            result = runner.invoke(app, ["generate-igtc", "2043", str(tmp_path / "igtc.ics")])

        assert result.exit_code == 1

    def test_missing_year_argument_fails(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["generate-igtc", str(tmp_path / "igtc.ics")])
        assert result.exit_code != 0


class TestGenerateIgtcIcsContent:
    def test_ics_contains_vevent(self, tmp_path: Path) -> None:
        output = tmp_path / "igtc.ics"
        _run_generate_igtc(2044, output, _fallback_to_bathurst())
        assert "BEGIN:VEVENT" in output.read_text()

    def test_ics_uid_contains_series_key(self, tmp_path: Path) -> None:
        output = tmp_path / "igtc.ics"
        _run_generate_igtc(2045, output, _fallback_to_bathurst())
        assert "igtc-2045-" in output.read_text()

    def test_no_duplicate_uids(self, tmp_path: Path) -> None:
        import re

        output = tmp_path / "igtc.ics"
        _run_generate_igtc(2046, output, _fallback_to_bathurst())
        unfolded = re.sub(r"\r?\n ", "", output.read_text())
        uids = re.findall(r"^UID:(.+)$", unfolded, re.MULTILINE)
        assert len(uids) == len(set(uids)), "Duplicate UIDs detected in ICS output"

    def test_five_vevents_per_round_twenty_five_total(self, tmp_path: Path) -> None:
        output = tmp_path / "igtc.ics"
        _run_generate_igtc(2047, output, _fallback_to_bathurst())
        assert output.read_text().count("BEGIN:VEVENT") == 25
