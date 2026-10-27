"""CLI integration tests for `motocal generate-moto3`.

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

_PATCH_TARGET = "motorsport_calendar.providers.moto3.sources.pulselive.PulseliveSource.fetch_json"


def _run_generate_moto3(
    year: int,
    output: Path,
    fetch_json_effect: Any,
    extra_args: list[str] | None = None,
) -> Any:
    args = ["generate-moto3", str(year), str(output)] + (extra_args or [])
    with patch(_PATCH_TARGET, new=AsyncMock(side_effect=fetch_json_effect)):
        return runner.invoke(app, args)


async def _events_effect(url: str, params: dict) -> list:
    return _EVENTS_FIXTURE


async def _empty_effect(url: str, params: dict) -> list:
    return []


class TestGenerateMoto3HappyPath:
    def test_exit_code_zero_on_success(self, tmp_path: Path) -> None:
        result = _run_generate_moto3(2052, tmp_path / "moto3.ics", _events_effect)
        assert result.exit_code == 0, result.output

    def test_ics_file_created(self, tmp_path: Path) -> None:
        output = tmp_path / "moto3.ics"
        _run_generate_moto3(2053, output, _events_effect)
        assert output.exists()

    def test_output_mentions_three_events(self, tmp_path: Path) -> None:
        result = _run_generate_moto3(2054, tmp_path / "moto3.ics", _events_effect)
        assert "3 event" in result.output

    def test_output_mentions_moto3_label(self, tmp_path: Path) -> None:
        result = _run_generate_moto3(2055, tmp_path / "moto3.ics", _events_effect)
        assert "Moto3" in result.output

    def test_empty_events_produces_empty_ics(self, tmp_path: Path) -> None:
        output = tmp_path / "moto3.ics"
        result = _run_generate_moto3(2056, output, _empty_effect)
        assert result.exit_code == 0
        assert "0 event" in result.output

    def test_refresh_flag_accepted(self, tmp_path: Path) -> None:
        result = _run_generate_moto3(
            2057, tmp_path / "moto3.ics", _events_effect, extra_args=["--refresh"]
        )
        assert result.exit_code == 0

    def test_fifteen_sessions_across_three_rounds(self, tmp_path: Path) -> None:
        result = _run_generate_moto3(2058, tmp_path / "moto3.ics", _events_effect)
        assert "15 session" in result.output


class TestGenerateMoto3Errors:
    def test_http_error_exits_with_code_1(self, tmp_path: Path) -> None:
        import httpx

        request = httpx.Request("GET", "https://example.com")
        response = httpx.Response(503, request=request)
        exc = httpx.HTTPStatusError("HTTP 503", request=request, response=response)

        with patch(_PATCH_TARGET, new=AsyncMock(side_effect=exc)):
            result = runner.invoke(app, ["generate-moto3", "2059", str(tmp_path / "m.ics")])

        assert result.exit_code == 1
        assert "Moto3 source error" in result.output

    def test_timeout_exits_with_code_1(self, tmp_path: Path) -> None:
        import httpx

        with patch(_PATCH_TARGET, new=AsyncMock(side_effect=httpx.TimeoutException("timeout"))):
            result = runner.invoke(app, ["generate-moto3", "2060", str(tmp_path / "m.ics")])

        assert result.exit_code == 1

    def test_missing_year_argument_fails(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["generate-moto3", str(tmp_path / "m.ics")])
        assert result.exit_code != 0


class TestGenerateMoto3IcsContent:
    def test_ics_contains_vevent(self, tmp_path: Path) -> None:
        output = tmp_path / "moto3.ics"
        _run_generate_moto3(2095, output, _events_effect)
        assert "BEGIN:VEVENT" in output.read_text()

    def test_ics_uid_contains_series_key(self, tmp_path: Path) -> None:
        output = tmp_path / "moto3.ics"
        _run_generate_moto3(2096, output, _events_effect)
        assert "moto3-2096-" in output.read_text()

    def test_no_duplicate_uids(self, tmp_path: Path) -> None:
        import re

        output = tmp_path / "moto3.ics"
        _run_generate_moto3(2097, output, _events_effect)
        unfolded = re.sub(r"\r?\n ", "", output.read_text())
        uids = re.findall(r"^UID:(.+)$", unfolded, re.MULTILINE)
        assert len(uids) == len(set(uids)), "Duplicate UIDs detected in ICS output"

    def test_fifteen_vevents_total(self, tmp_path: Path) -> None:
        output = tmp_path / "moto3.ics"
        _run_generate_moto3(2098, output, _events_effect)
        assert output.read_text().count("BEGIN:VEVENT") == 15
