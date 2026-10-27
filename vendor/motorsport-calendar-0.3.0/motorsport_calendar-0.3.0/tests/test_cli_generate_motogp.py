"""CLI integration tests for `motocal generate-motogp`.

PulseliveSource.fetch_json is mocked at the source level, using the real
captured fixture in tests/fixtures/real/motogp_events_2026.json (trimmed,
never hand-crafted — same fixture used by test_pulselive_base.py). The
fixture has 5 entries (1 TEST, 1 MEDIA, 3 GP) — only the 3 "GP" rounds
survive filtering.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

from typer.testing import CliRunner

from motorsport_calendar.cli import app

runner = CliRunner()

_FIXTURES_DIR = Path(__file__).parent / "fixtures" / "real"
_EVENTS_FIXTURE = json.loads((_FIXTURES_DIR / "motogp_events_2026.json").read_text())

_PATCH_TARGET = "motorsport_calendar.providers.motogp.sources.pulselive.PulseliveSource.fetch_json"


def _run_generate_motogp(
    year: int,
    output: Path,
    fetch_json_effect: Any,
    extra_args: list[str] | None = None,
) -> Any:
    args = ["generate-motogp", str(year), str(output)] + (extra_args or [])
    with patch(_PATCH_TARGET, new=AsyncMock(side_effect=fetch_json_effect)):
        return runner.invoke(app, args)


async def _events_effect(url: str, params: dict) -> list:
    return _EVENTS_FIXTURE


async def _empty_effect(url: str, params: dict) -> list:
    return []


class TestGenerateMotoGpHappyPath:
    def test_exit_code_zero_on_success(self, tmp_path: Path) -> None:
        result = _run_generate_motogp(2026, tmp_path / "motogp.ics", _events_effect)
        assert result.exit_code == 0, result.output

    def test_ics_file_created(self, tmp_path: Path) -> None:
        output = tmp_path / "motogp.ics"
        _run_generate_motogp(2027, output, _events_effect)
        assert output.exists()

    def test_ics_contains_vcalendar_header(self, tmp_path: Path) -> None:
        output = tmp_path / "motogp.ics"
        _run_generate_motogp(2028, output, _events_effect)
        assert "BEGIN:VCALENDAR" in output.read_text()

    def test_output_mentions_three_events(self, tmp_path: Path) -> None:
        result = _run_generate_motogp(2029, tmp_path / "motogp.ics", _events_effect)
        assert "3 event" in result.output

    def test_output_mentions_motogp_label(self, tmp_path: Path) -> None:
        result = _run_generate_motogp(2030, tmp_path / "motogp.ics", _events_effect)
        assert "MotoGP" in result.output

    def test_output_mentions_source_name(self, tmp_path: Path) -> None:
        result = _run_generate_motogp(2031, tmp_path / "motogp.ics", _events_effect)
        assert "pulselive" in result.output

    def test_empty_events_produces_empty_ics(self, tmp_path: Path) -> None:
        output = tmp_path / "motogp.ics"
        result = _run_generate_motogp(2032, output, _empty_effect)
        assert result.exit_code == 0
        assert "0 event" in result.output

    def test_refresh_flag_accepted(self, tmp_path: Path) -> None:
        result = _run_generate_motogp(
            2033, tmp_path / "motogp.ics", _events_effect, extra_args=["--refresh"]
        )
        assert result.exit_code == 0

    def test_eighteen_sessions_across_three_rounds(self, tmp_path: Path) -> None:
        # 3 GP rounds x 6 MotoGP sessions each (FP1/FP2/FP3/Qualifying/Sprint/Race)
        result = _run_generate_motogp(2034, tmp_path / "motogp.ics", _events_effect)
        assert "18 session" in result.output


class TestGenerateMotoGpErrors:
    def test_http_error_exits_with_code_1(self, tmp_path: Path) -> None:
        import httpx

        request = httpx.Request("GET", "https://example.com")
        response = httpx.Response(503, request=request)
        exc = httpx.HTTPStatusError("HTTP 503", request=request, response=response)

        with patch(_PATCH_TARGET, new=AsyncMock(side_effect=exc)):
            result = runner.invoke(app, ["generate-motogp", "2035", str(tmp_path / "m.ics")])

        assert result.exit_code == 1
        assert "MotoGP source error" in result.output

    def test_timeout_exits_with_code_1(self, tmp_path: Path) -> None:
        import httpx

        with patch(_PATCH_TARGET, new=AsyncMock(side_effect=httpx.TimeoutException("timeout"))):
            result = runner.invoke(app, ["generate-motogp", "2036", str(tmp_path / "m.ics")])

        assert result.exit_code == 1

    def test_missing_year_argument_fails(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["generate-motogp", str(tmp_path / "m.ics")])
        assert result.exit_code != 0


class TestGenerateMotoGpIcsContent:
    def test_ics_contains_vevent(self, tmp_path: Path) -> None:
        output = tmp_path / "motogp.ics"
        _run_generate_motogp(2037, output, _events_effect)
        assert "BEGIN:VEVENT" in output.read_text()

    def test_ics_uid_contains_series_key(self, tmp_path: Path) -> None:
        output = tmp_path / "motogp.ics"
        _run_generate_motogp(2038, output, _events_effect)
        assert "motogp-2038-" in output.read_text()

    def test_no_duplicate_uids(self, tmp_path: Path) -> None:
        import re

        output = tmp_path / "motogp.ics"
        _run_generate_motogp(2039, output, _events_effect)
        unfolded = re.sub(r"\r?\n ", "", output.read_text())
        uids = re.findall(r"^UID:(.+)$", unfolded, re.MULTILINE)
        assert len(uids) == len(set(uids)), "Duplicate UIDs detected in ICS output"

    def test_all_dtstart_are_utc(self, tmp_path: Path) -> None:
        import re

        output = tmp_path / "motogp.ics"
        _run_generate_motogp(2040, output, _events_effect)
        unfolded = re.sub(r"\r?\n ", "", output.read_text())
        dtstarts = re.findall(r"^DTSTART:(.+)$", unfolded, re.MULTILINE)
        assert dtstarts, "no DTSTART lines found"
        assert all(d.endswith("Z") for d in dtstarts)

    def test_six_vevents_per_round_eighteen_total(self, tmp_path: Path) -> None:
        output = tmp_path / "motogp.ics"
        _run_generate_motogp(2041, output, _events_effect)
        assert output.read_text().count("BEGIN:VEVENT") == 18
