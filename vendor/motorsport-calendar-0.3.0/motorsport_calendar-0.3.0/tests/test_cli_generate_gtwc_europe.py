"""CLI integration tests for `motocal generate-gtwc-europe`.

SroScraperSource.fetch_html is mocked at the URL level (calendar page vs
per-round event page), using the real captured fixtures in
tests/fixtures/real/ — same fixtures used by test_sro_timetable_base.py.

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


_CALENDAR_TEN_ROUNDS = load_real_fixture("gtwc_europe_calendar.html")
_EVENT_MISANO = load_real_fixture("gtwc_europe_event_misano.html")
_CALENDAR_EMPTY = "<html><body>no rounds this year</body></html>"

_PATCH_TARGET = (
    "motorsport_calendar.providers.gtwc_europe.sources.sro_scraper.SroScraperSource.fetch_html"
)


def _run_generate_gtwc_europe(
    year: int,
    output: Path,
    fetch_html_effect: Any = None,
    extra_args: list[str] | None = None,
) -> Any:
    # Any URL that isn't "/calendar" falls back to the Misano fixture — the
    # per-round slug still comes from the URL itself, so UIDs stay unique
    # across all 10 rounds even though every round returns the same body.
    effect = fetch_html_effect or _fetch_html_side_effect(("/calendar", _CALENDAR_TEN_ROUNDS))
    args = ["generate-gtwc-europe", str(year), str(output)] + (extra_args or [])
    with patch(_PATCH_TARGET, new=AsyncMock(side_effect=effect)):
        return runner.invoke(app, args)


def _fallback_to_misano() -> Any:
    async def _fake_fetch_html(url: str) -> str:
        if "/calendar" in url:
            return _CALENDAR_TEN_ROUNDS
        return _EVENT_MISANO

    return _fake_fetch_html


class TestGenerateGtwcEuropeHappyPath:
    def test_exit_code_zero_on_success(self, tmp_path: Path) -> None:
        result = _run_generate_gtwc_europe(2051, tmp_path / "gtwce.ics", _fallback_to_misano())
        assert result.exit_code == 0, result.output

    def test_ics_file_created(self, tmp_path: Path) -> None:
        output = tmp_path / "gtwce.ics"
        _run_generate_gtwc_europe(2052, output, _fallback_to_misano())
        assert output.exists()

    def test_ics_contains_vcalendar_header(self, tmp_path: Path) -> None:
        output = tmp_path / "gtwce.ics"
        _run_generate_gtwc_europe(2053, output, _fallback_to_misano())
        assert "BEGIN:VCALENDAR" in output.read_text()

    def test_output_mentions_ten_events(self, tmp_path: Path) -> None:
        result = _run_generate_gtwc_europe(2054, tmp_path / "gtwce.ics", _fallback_to_misano())
        assert "10 event" in result.output

    def test_output_mentions_gtwc_europe_label(self, tmp_path: Path) -> None:
        result = _run_generate_gtwc_europe(2055, tmp_path / "gtwce.ics", _fallback_to_misano())
        assert "GT World Challenge Europe" in result.output

    def test_output_mentions_source_name(self, tmp_path: Path) -> None:
        result = _run_generate_gtwc_europe(2056, tmp_path / "gtwce.ics", _fallback_to_misano())
        assert "sro_scraper" in result.output

    def test_empty_calendar_produces_empty_ics(self, tmp_path: Path) -> None:
        output = tmp_path / "gtwce.ics"
        result = _run_generate_gtwc_europe(
            2057, output, _fetch_html_side_effect(("/calendar", _CALENDAR_EMPTY))
        )
        assert result.exit_code == 0
        assert "0 event" in result.output

    def test_refresh_flag_accepted(self, tmp_path: Path) -> None:
        result = _run_generate_gtwc_europe(
            2058, tmp_path / "gtwce.ics", _fallback_to_misano(), extra_args=["--refresh"]
        )
        assert result.exit_code == 0

    def test_sixty_sessions_across_ten_rounds(self, tmp_path: Path) -> None:
        # 10 rounds x 6 sessions each (Misano fixture reused for every round)
        result = _run_generate_gtwc_europe(2059, tmp_path / "gtwce.ics", _fallback_to_misano())
        assert "60 session" in result.output


class TestGenerateGtwcEuropeErrors:
    def test_http_error_exits_with_code_1(self, tmp_path: Path) -> None:
        import httpx

        request = httpx.Request("GET", "https://example.com")
        response = httpx.Response(503, request=request)
        exc = httpx.HTTPStatusError("HTTP 503", request=request, response=response)

        with patch(_PATCH_TARGET, new=AsyncMock(side_effect=exc)):
            result = runner.invoke(
                app, ["generate-gtwc-europe", "2060", str(tmp_path / "gtwce.ics")]
            )

        assert result.exit_code == 1

    def test_http_error_message_mentions_source(self, tmp_path: Path) -> None:
        import httpx

        request = httpx.Request("GET", "https://example.com")
        response = httpx.Response(503, request=request)
        exc = httpx.HTTPStatusError("HTTP 503", request=request, response=response)

        with patch(_PATCH_TARGET, new=AsyncMock(side_effect=exc)):
            result = runner.invoke(
                app, ["generate-gtwc-europe", "2061", str(tmp_path / "gtwce.ics")]
            )

        assert "GT World Challenge Europe source error" in result.output

    def test_timeout_exits_with_code_1(self, tmp_path: Path) -> None:
        import httpx

        with patch(_PATCH_TARGET, new=AsyncMock(side_effect=httpx.TimeoutException("timeout"))):
            result = runner.invoke(
                app, ["generate-gtwc-europe", "2062", str(tmp_path / "gtwce.ics")]
            )

        assert result.exit_code == 1

    def test_missing_year_argument_fails(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["generate-gtwc-europe", str(tmp_path / "gtwce.ics")])
        assert result.exit_code != 0


class TestGenerateGtwcEuropeIcsContent:
    def test_ics_contains_vevent(self, tmp_path: Path) -> None:
        output = tmp_path / "gtwce.ics"
        _run_generate_gtwc_europe(2063, output, _fallback_to_misano())
        assert "BEGIN:VEVENT" in output.read_text()

    def test_ics_contains_race(self, tmp_path: Path) -> None:
        output = tmp_path / "gtwce.ics"
        _run_generate_gtwc_europe(2064, output, _fallback_to_misano())
        assert "Race" in output.read_text()

    def test_ics_uid_contains_series_key(self, tmp_path: Path) -> None:
        output = tmp_path / "gtwce.ics"
        _run_generate_gtwc_europe(2066, output, _fallback_to_misano())
        assert "gtwc-europe-2066-" in output.read_text()

    def test_no_duplicate_uids(self, tmp_path: Path) -> None:
        """RFC 5545: UIDs must be unique within a calendar.

        Unfolds RFC 5545 continuation lines first (a single space at the
        start of a line means "this is a continuation of the previous
        line") — this project's longer slug-based UIDs can exceed the
        75-octet fold width, unlike the shorter ACO/ELMS UIDs.
        """
        import re

        output = tmp_path / "gtwce.ics"
        _run_generate_gtwc_europe(2067, output, _fallback_to_misano())
        unfolded = re.sub(r"\r?\n ", "", output.read_text())
        uids = re.findall(r"^UID:(.+)$", unfolded, re.MULTILINE)
        assert len(uids) == len(set(uids)), "Duplicate UIDs detected in ICS output"

    def test_six_vevents_per_round_sixty_total(self, tmp_path: Path) -> None:
        output = tmp_path / "gtwce.ics"
        _run_generate_gtwc_europe(2068, output, _fallback_to_misano())
        assert output.read_text().count("BEGIN:VEVENT") == 60
