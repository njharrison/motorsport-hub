"""CLI integration tests for `motocal generate-gtwc-asia`.

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


_CALENDAR_SIX_ROUNDS = load_real_fixture("gtwc_asia_calendar.html")
_EVENT_SEPANG = load_real_fixture("gtwc_asia_event_sepang.html")
_CALENDAR_EMPTY = "<html><body>no rounds this year</body></html>"

_PATCH_TARGET = (
    "motorsport_calendar.providers.gtwc_asia.sources.sro_scraper.SroScraperSource.fetch_html"
)


def _fallback_to_sepang() -> Any:
    async def _fake_fetch_html(url: str) -> str:
        if "/calendar" in url:
            return _CALENDAR_SIX_ROUNDS
        return _EVENT_SEPANG

    return _fake_fetch_html


def _empty_calendar() -> Any:
    async def _fake_fetch_html(url: str) -> str:
        return _CALENDAR_EMPTY

    return _fake_fetch_html


def _run_generate_gtwc_asia(
    year: int,
    output: Path,
    fetch_html_effect: Any,
    extra_args: list[str] | None = None,
) -> Any:
    args = ["generate-gtwc-asia", str(year), str(output)] + (extra_args or [])
    with patch(_PATCH_TARGET, new=AsyncMock(side_effect=fetch_html_effect)):
        return runner.invoke(app, args)


class TestGenerateGtwcAsiaHappyPath:
    def test_exit_code_zero_on_success(self, tmp_path: Path) -> None:
        result = _run_generate_gtwc_asia(2091, tmp_path / "gtwcasia.ics", _fallback_to_sepang())
        assert result.exit_code == 0, result.output

    def test_ics_file_created(self, tmp_path: Path) -> None:
        output = tmp_path / "gtwcasia.ics"
        _run_generate_gtwc_asia(2092, output, _fallback_to_sepang())
        assert output.exists()

    def test_output_mentions_six_events(self, tmp_path: Path) -> None:
        result = _run_generate_gtwc_asia(2093, tmp_path / "gtwcasia.ics", _fallback_to_sepang())
        assert "6 event" in result.output

    def test_output_mentions_gtwc_asia_label(self, tmp_path: Path) -> None:
        result = _run_generate_gtwc_asia(2094, tmp_path / "gtwcasia.ics", _fallback_to_sepang())
        assert "GT World Challenge Asia" in result.output

    def test_empty_calendar_produces_empty_ics(self, tmp_path: Path) -> None:
        output = tmp_path / "gtwcasia.ics"
        result = _run_generate_gtwc_asia(2095, output, _empty_calendar())
        assert result.exit_code == 0
        assert "0 event" in result.output

    def test_refresh_flag_accepted(self, tmp_path: Path) -> None:
        result = _run_generate_gtwc_asia(
            2096, tmp_path / "gtwcasia.ics", _fallback_to_sepang(), extra_args=["--refresh"]
        )
        assert result.exit_code == 0


class TestGenerateGtwcAsiaErrors:
    def test_http_error_exits_with_code_1(self, tmp_path: Path) -> None:
        import httpx

        request = httpx.Request("GET", "https://example.com")
        response = httpx.Response(503, request=request)
        exc = httpx.HTTPStatusError("HTTP 503", request=request, response=response)

        with patch(_PATCH_TARGET, new=AsyncMock(side_effect=exc)):
            result = runner.invoke(
                app, ["generate-gtwc-asia", "2097", str(tmp_path / "gtwcasia.ics")]
            )

        assert result.exit_code == 1
        assert "GT World Challenge Asia source error" in result.output

    def test_timeout_exits_with_code_1(self, tmp_path: Path) -> None:
        import httpx

        with patch(_PATCH_TARGET, new=AsyncMock(side_effect=httpx.TimeoutException("timeout"))):
            result = runner.invoke(
                app, ["generate-gtwc-asia", "2098", str(tmp_path / "gtwcasia.ics")]
            )

        assert result.exit_code == 1

    def test_missing_year_argument_fails(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["generate-gtwc-asia", str(tmp_path / "gtwcasia.ics")])
        assert result.exit_code != 0


class TestGenerateGtwcAsiaIcsContent:
    def test_ics_contains_vevent(self, tmp_path: Path) -> None:
        output = tmp_path / "gtwcasia.ics"
        _run_generate_gtwc_asia(2099, output, _fallback_to_sepang())
        assert "BEGIN:VEVENT" in output.read_text()

    def test_ics_uid_contains_series_key(self, tmp_path: Path) -> None:
        output = tmp_path / "gtwcasia.ics"
        _run_generate_gtwc_asia(2089, output, _fallback_to_sepang())
        assert "gtwc-asia-2089-" in output.read_text()

    def test_no_duplicate_uids(self, tmp_path: Path) -> None:
        import re

        output = tmp_path / "gtwcasia.ics"
        _run_generate_gtwc_asia(2090, output, _fallback_to_sepang())
        unfolded = re.sub(r"\r?\n ", "", output.read_text())
        uids = re.findall(r"^UID:(.+)$", unfolded, re.MULTILINE)
        assert len(uids) == len(set(uids)), "Duplicate UIDs detected in ICS output"
