"""Integration tests for the `motocal generate` CLI command.

Strategy:
- F1 : patch OpenF1Source._get_json avec AsyncMock (side_effect=[meetings, sessions])
- WEC : patch OfficialWecSource.get_season avec AsyncMock (return_value=wec_events)
- OfficialWecSource est une implémentation réelle depuis le Sprint 48 (fiawec.com,
  voir tests/test_wec_provider.py) — pour les scénarios "WEC échoue", get_season
  doit désormais être explicitement mocké en échec (plus de NotImplementedError
  naturel à s'appuyer dessus)
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from typer.testing import CliRunner

from motorsport_calendar.cli import app
from motorsport_calendar.models import (
    Championship,
    ChampionshipCategory,
    Circuit,
    Event,
    Session,
    SessionType,
)
from motorsport_calendar.providers.elms.sources.aco_scraper import (
    AcoScraperSource as ElmsAcoScraperSource,
)
from motorsport_calendar.providers.f1_academy.sources.f1calendar import (
    F1CalendarSource as F1AcademyCalendarSource,
)
from motorsport_calendar.providers.formula1.sources.openf1 import OpenF1Source
from motorsport_calendar.providers.formula2.sources.f1calendar import (
    F1CalendarSource as F2CalendarSource,
)
from motorsport_calendar.providers.formula3.sources.f1calendar import (
    F1CalendarSource as F3CalendarSource,
)
from motorsport_calendar.providers.formula_e.sources.f1calendar import (
    F1CalendarSource as FormulaECalendarSource,
)
from motorsport_calendar.providers.gtwc_america.sources.sro_scraper import (
    SroScraperSource as GtwcAmericaSroScraperSource,
)
from motorsport_calendar.providers.gtwc_asia.sources.sro_scraper import (
    SroScraperSource as GtwcAsiaSroScraperSource,
)
from motorsport_calendar.providers.gtwc_europe.sources.sro_scraper import (
    SroScraperSource as GtwcEuropeSroScraperSource,
)
from motorsport_calendar.providers.igtc.sources.sro_scraper import (
    SroScraperSource as IgtcSroScraperSource,
)
from motorsport_calendar.providers.mlmc.sources.aco_scraper import (
    AcoScraperSource as MlmcAcoScraperSource,
)
from motorsport_calendar.providers.moto2.sources.pulselive import (
    PulseliveSource as Moto2PulseliveSource,
)
from motorsport_calendar.providers.moto3.sources.pulselive import (
    PulseliveSource as Moto3PulseliveSource,
)
from motorsport_calendar.providers.motogp.sources.pulselive import (
    PulseliveSource as MotoGpPulseliveSource,
)
from motorsport_calendar.providers.wec.sources.official import OfficialWecSource

runner = CliRunner()

# ---------------------------------------------------------------------------
# Données F1 — mirrors OpenF1 API response shape
# ---------------------------------------------------------------------------

_F1_MEETINGS = [
    {
        "meeting_key": 1217,
        "meeting_name": "Bahrain Grand Prix",
        "location": "Sakhir",
        "country_name": "Bahrain",
        "circuit_short_name": "Sakhir",
        "circuit_key": 1,
        "year": 2024,
        "date_start": "2024-02-29T09:00:00+00:00",
    },
    {
        "meeting_key": 1218,
        "meeting_name": "Saudi Arabian Grand Prix",
        "location": "Jeddah",
        "country_name": "Saudi Arabia",
        "circuit_short_name": "Jeddah",
        "circuit_key": 2,
        "year": 2024,
        "date_start": "2024-03-07T09:00:00+00:00",
    },
]

_F1_SESSIONS = [
    {
        "session_key": 9472,
        "meeting_key": 1217,
        "session_name": "Race",
        "date_start": "2024-03-02T15:00:00+00:00",
        "date_end": "2024-03-02T17:00:00+00:00",
    },
    {
        "session_key": 9473,
        "meeting_key": 1217,
        "session_name": "Qualifying",
        "date_start": "2024-03-01T15:00:00+00:00",
        "date_end": "2024-03-01T16:00:00+00:00",
    },
    {
        "session_key": 9490,
        "meeting_key": 1218,
        "session_name": "Race",
        "date_start": "2024-03-09T18:00:00+00:00",
        "date_end": "2024-03-09T20:00:00+00:00",
    },
]

_F1_SESSION_COUNT = 3  # 2 Bahrain + 1 Saudi

# ---------------------------------------------------------------------------
# Données WEC
# ---------------------------------------------------------------------------

_WEC_CHAMPIONSHIP = Championship(
    id="wec-2024",
    name="FIA World Endurance Championship",
    category=ChampionshipCategory.ENDURANCE,
)

_WEC_EVENTS = [
    Event(
        event_uid="wec-2024-01-sebring",
        championship=_WEC_CHAMPIONSHIP,
        season=2024,
        round=1,
        name="1000 Miles of Sebring",
        circuit=Circuit(
            id="sebring",
            name="Sebring International Raceway",
            city="Sebring",
            country="USA",
            timezone="America/New_York",
        ),
        sessions=(
            Session(
                type=SessionType.RACE,
                title="Race",
                start_datetime=datetime(2024, 3, 16, 16, 0, tzinfo=UTC),
                end_datetime=datetime(2024, 3, 16, 22, 0, tzinfo=UTC),
            ),
        ),
    ),
    Event(
        event_uid="wec-2024-02-spa",
        championship=_WEC_CHAMPIONSHIP,
        season=2024,
        round=2,
        name="6 Hours of Spa-Francorchamps",
        circuit=Circuit(
            id="spa",
            name="Circuit de Spa-Francorchamps",
            city="Spa",
            country="Belgium",
            timezone="Europe/Brussels",
        ),
        sessions=(
            Session(
                type=SessionType.HYPERPOLE,
                title="Hyperpole",
                start_datetime=datetime(2024, 5, 10, 9, 0, tzinfo=UTC),
                end_datetime=datetime(2024, 5, 10, 9, 30, tzinfo=UTC),
            ),
            Session(
                type=SessionType.RACE,
                title="Race",
                start_datetime=datetime(2024, 5, 11, 13, 0, tzinfo=UTC),
                end_datetime=datetime(2024, 5, 11, 19, 0, tzinfo=UTC),
            ),
        ),
    ),
]

_WEC_SESSION_COUNT = 3  # 1 Sebring + 2 Spa

# Événements WEC antérieurs à F1 — pour le test de tri chronologique
_WEC_EVENTS_EARLY = [
    Event(
        event_uid="wec-2024-01-daytona",
        championship=_WEC_CHAMPIONSHIP,
        season=2024,
        round=1,
        name="Rolex 24 at Daytona",
        circuit=Circuit(
            id="daytona",
            name="Daytona International Speedway",
            city="Daytona Beach",
            country="USA",
            timezone="America/New_York",
        ),
        sessions=(
            Session(
                type=SessionType.RACE,
                title="Race",
                # Janvier — avant tous les events F1 de mars
                start_datetime=datetime(2024, 1, 27, 14, 0, tzinfo=UTC),
                end_datetime=datetime(2024, 1, 28, 14, 0, tzinfo=UTC),
            ),
        ),
    )
]


def _mock_f1(meetings: list, sessions: list) -> AsyncMock:
    return AsyncMock(side_effect=[meetings, sessions])


def _mock_wec(events: list) -> AsyncMock:
    return AsyncMock(return_value=events)


@pytest.fixture(autouse=True)
def _isolate_support_series():
    """Prevent F2/F3/F1-Academy/Formula E/ELMS/MLMC/GT series/Moto series/WEC
    from making real HTTP calls in every test.

    Tests that need specific per-championship behaviour (error paths etc.)
    override these mocks with explicit patch.object calls inside the test
    body — an inner `with patch.object(...)` block always wins over this
    outer one for its duration, then reverts cleanly on exit. ELMS/MLMC/GT
    series are scraped (fetch_html), not JSON-fetched — an empty season/
    calendar page (no race/round links) makes get_season() return [] the
    same way an empty {"races": []} payload does for the JSON-based
    sources. MotoGP/Moto2/Moto3 fetch a JSON *list* of events (not a
    {"races": [...]} dict) — an empty list makes get_season() return []
    the same way.

    WEC (OfficialWecSource, a real implementation since Sprint 48) defaults
    here to *failing* rather than an empty success — this preserves every
    existing "WEC fails naturally" test's premise (previously true because
    the stub always raised NotImplementedError when unmocked), without
    each such test needing its own explicit failure mock.
    """
    _empty = AsyncMock(return_value={"races": []})
    _empty_html = AsyncMock(return_value="<html><body>no races</body></html>")
    _empty_moto = AsyncMock(return_value=[])
    _wec_fails = AsyncMock(side_effect=NotImplementedError)
    with (
        patch.object(F2CalendarSource, "fetch_json", _empty),
        patch.object(F3CalendarSource, "fetch_json", _empty),
        patch.object(F1AcademyCalendarSource, "fetch_json", _empty),
        patch.object(FormulaECalendarSource, "fetch_json", _empty),
        patch.object(ElmsAcoScraperSource, "fetch_html", _empty_html),
        patch.object(MlmcAcoScraperSource, "fetch_html", _empty_html),
        patch.object(GtwcEuropeSroScraperSource, "fetch_html", _empty_html),
        patch.object(GtwcAmericaSroScraperSource, "fetch_html", _empty_html),
        patch.object(GtwcAsiaSroScraperSource, "fetch_html", _empty_html),
        patch.object(IgtcSroScraperSource, "fetch_html", _empty_html),
        patch.object(MotoGpPulseliveSource, "fetch_json", _empty_moto),
        patch.object(Moto2PulseliveSource, "fetch_json", _empty_moto),
        patch.object(Moto3PulseliveSource, "fetch_json", _empty_moto),
        patch.object(OfficialWecSource, "get_season", _wec_fails),
    ):
        yield


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


class TestGenerateHappyPath:
    def test_f1_succeeds_wec_fails_exits_zero(self, tmp_path: Path) -> None:
        with patch.object(OpenF1Source, "_get_json", _mock_f1(_F1_MEETINGS, _F1_SESSIONS)):
            result = runner.invoke(app, ["generate", "2024", str(tmp_path / "all.ics")])
        assert result.exit_code == 0

    def test_f1_succeeds_wec_fails_creates_file(self, tmp_path: Path) -> None:
        output = tmp_path / "all.ics"
        with patch.object(OpenF1Source, "_get_json", _mock_f1(_F1_MEETINGS, _F1_SESSIONS)):
            runner.invoke(app, ["generate", "2024", str(output)])
        assert output.exists()
        assert output.stat().st_size > 0

    def test_f1_succeeds_wec_fails_vevent_count_is_f1_only(self, tmp_path: Path) -> None:
        output = tmp_path / "all.ics"
        _empty = AsyncMock(return_value={"races": []})
        with (
            patch.object(OpenF1Source, "_get_json", _mock_f1(_F1_MEETINGS, _F1_SESSIONS)),
            patch.object(F2CalendarSource, "fetch_json", _empty),
            patch.object(F3CalendarSource, "fetch_json", _empty),
            patch.object(F1AcademyCalendarSource, "fetch_json", _empty),
        ):
            runner.invoke(app, ["generate", "2024", str(output)])
        content = output.read_text(encoding="utf-8")
        assert content.count("BEGIN:VEVENT") == _F1_SESSION_COUNT

    def test_both_succeed_exits_zero(self, tmp_path: Path) -> None:
        with (
            patch.object(OpenF1Source, "_get_json", _mock_f1(_F1_MEETINGS, _F1_SESSIONS)),
            patch.object(OfficialWecSource, "get_season", _mock_wec(_WEC_EVENTS)),
        ):
            result = runner.invoke(app, ["generate", "2024", str(tmp_path / "all.ics")])
        assert result.exit_code == 0

    def test_both_succeed_vevent_count_is_sum_of_all_sessions(self, tmp_path: Path) -> None:
        output = tmp_path / "all.ics"
        _empty = AsyncMock(return_value={"races": []})
        with (
            patch.object(OpenF1Source, "_get_json", _mock_f1(_F1_MEETINGS, _F1_SESSIONS)),
            patch.object(OfficialWecSource, "get_season", _mock_wec(_WEC_EVENTS)),
            patch.object(F2CalendarSource, "fetch_json", _empty),
            patch.object(F3CalendarSource, "fetch_json", _empty),
            patch.object(F1AcademyCalendarSource, "fetch_json", _empty),
        ):
            runner.invoke(app, ["generate", "2024", str(output)])
        content = output.read_text(encoding="utf-8")
        assert content.count("BEGIN:VEVENT") == _F1_SESSION_COUNT + _WEC_SESSION_COUNT

    def test_both_succeed_file_contains_vcalendar(self, tmp_path: Path) -> None:
        output = tmp_path / "all.ics"
        with (
            patch.object(OpenF1Source, "_get_json", _mock_f1(_F1_MEETINGS, _F1_SESSIONS)),
            patch.object(OfficialWecSource, "get_season", _mock_wec(_WEC_EVENTS)),
        ):
            runner.invoke(app, ["generate", "2024", str(output)])
        content = output.read_text(encoding="utf-8")
        assert "BEGIN:VCALENDAR" in content
        assert "END:VCALENDAR" in content

    def test_f1_success_summary_shows_checkmark(self, tmp_path: Path) -> None:
        with patch.object(OpenF1Source, "_get_json", _mock_f1(_F1_MEETINGS, _F1_SESSIONS)):
            result = runner.invoke(app, ["generate", "2024", str(tmp_path / "all.ics")])
        assert "✓" in result.output

    def test_wec_failure_summary_shows_failure_marker(self, tmp_path: Path) -> None:
        # WEC échoue naturellement (stub NotImplementedError)
        with patch.object(OpenF1Source, "_get_json", _mock_f1(_F1_MEETINGS, _F1_SESSIONS)):
            result = runner.invoke(app, ["generate", "2024", str(tmp_path / "all.ics")])
        assert "✗" in result.output

    def test_empty_f1_season_still_exits_zero(self, tmp_path: Path) -> None:
        # 0 événements F1 mais fetch réussi → exit 0
        with patch.object(OpenF1Source, "_get_json", _mock_f1([], [])):
            result = runner.invoke(app, ["generate", "2024", str(tmp_path / "all.ics")])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Error path
# ---------------------------------------------------------------------------


class TestGenerateErrors:
    def test_all_providers_fail_exits_one(self, tmp_path: Path) -> None:
        request = httpx.Request("GET", "https://api.openf1.org/v1/meetings")
        response = httpx.Response(503, request=request)
        http_fail = httpx.HTTPStatusError("503", request=request, response=response)
        f1_fail = AsyncMock(side_effect=http_fail)
        f2_fail = AsyncMock(side_effect=http_fail)
        f3_fail = AsyncMock(side_effect=http_fail)
        f1a_fail = AsyncMock(side_effect=http_fail)
        fe_fail = AsyncMock(side_effect=http_fail)
        elms_fail = AsyncMock(side_effect=http_fail)
        mlmc_fail = AsyncMock(side_effect=http_fail)
        gtwc_europe_fail = AsyncMock(side_effect=http_fail)
        gtwc_america_fail = AsyncMock(side_effect=http_fail)
        gtwc_asia_fail = AsyncMock(side_effect=http_fail)
        igtc_fail = AsyncMock(side_effect=http_fail)
        motogp_fail = AsyncMock(side_effect=http_fail)
        moto2_fail = AsyncMock(side_effect=http_fail)
        moto3_fail = AsyncMock(side_effect=http_fail)
        with (
            patch.object(OpenF1Source, "_get_json", f1_fail),
            patch.object(F2CalendarSource, "fetch_json", f2_fail),
            patch.object(F3CalendarSource, "fetch_json", f3_fail),
            patch.object(F1AcademyCalendarSource, "fetch_json", f1a_fail),
            patch.object(FormulaECalendarSource, "fetch_json", fe_fail),
            patch.object(ElmsAcoScraperSource, "fetch_html", elms_fail),
            patch.object(MlmcAcoScraperSource, "fetch_html", mlmc_fail),
            patch.object(GtwcEuropeSroScraperSource, "fetch_html", gtwc_europe_fail),
            patch.object(GtwcAmericaSroScraperSource, "fetch_html", gtwc_america_fail),
            patch.object(GtwcAsiaSroScraperSource, "fetch_html", gtwc_asia_fail),
            patch.object(IgtcSroScraperSource, "fetch_html", igtc_fail),
            patch.object(MotoGpPulseliveSource, "fetch_json", motogp_fail),
            patch.object(Moto2PulseliveSource, "fetch_json", moto2_fail),
            patch.object(Moto3PulseliveSource, "fetch_json", moto3_fail),
        ):
            result = runner.invoke(app, ["generate", "2024", str(tmp_path / "all.ics")])
        assert result.exit_code == 1

    def test_all_providers_fail_no_file_created(self, tmp_path: Path) -> None:
        output = tmp_path / "all.ics"
        request = httpx.Request("GET", "https://api.openf1.org/v1/meetings")
        response = httpx.Response(503, request=request)
        http_fail = httpx.HTTPStatusError("503", request=request, response=response)
        f1_fail = AsyncMock(side_effect=http_fail)
        f2_fail = AsyncMock(side_effect=http_fail)
        f3_fail = AsyncMock(side_effect=http_fail)
        f1a_fail = AsyncMock(side_effect=http_fail)
        fe_fail = AsyncMock(side_effect=http_fail)
        elms_fail = AsyncMock(side_effect=http_fail)
        mlmc_fail = AsyncMock(side_effect=http_fail)
        gtwc_europe_fail = AsyncMock(side_effect=http_fail)
        gtwc_america_fail = AsyncMock(side_effect=http_fail)
        gtwc_asia_fail = AsyncMock(side_effect=http_fail)
        igtc_fail = AsyncMock(side_effect=http_fail)
        motogp_fail = AsyncMock(side_effect=http_fail)
        moto2_fail = AsyncMock(side_effect=http_fail)
        moto3_fail = AsyncMock(side_effect=http_fail)
        with (
            patch.object(OpenF1Source, "_get_json", f1_fail),
            patch.object(F2CalendarSource, "fetch_json", f2_fail),
            patch.object(F3CalendarSource, "fetch_json", f3_fail),
            patch.object(F1AcademyCalendarSource, "fetch_json", f1a_fail),
            patch.object(FormulaECalendarSource, "fetch_json", fe_fail),
            patch.object(ElmsAcoScraperSource, "fetch_html", elms_fail),
            patch.object(MlmcAcoScraperSource, "fetch_html", mlmc_fail),
            patch.object(GtwcEuropeSroScraperSource, "fetch_html", gtwc_europe_fail),
            patch.object(GtwcAmericaSroScraperSource, "fetch_html", gtwc_america_fail),
            patch.object(GtwcAsiaSroScraperSource, "fetch_html", gtwc_asia_fail),
            patch.object(IgtcSroScraperSource, "fetch_html", igtc_fail),
            patch.object(MotoGpPulseliveSource, "fetch_json", motogp_fail),
            patch.object(Moto2PulseliveSource, "fetch_json", moto2_fail),
            patch.object(Moto3PulseliveSource, "fetch_json", moto3_fail),
        ):
            runner.invoke(app, ["generate", "2024", str(output)])
        assert not output.exists()

    def test_f1_http_error_wec_succeeds_exits_zero(self, tmp_path: Path) -> None:
        request = httpx.Request("GET", "https://api.openf1.org/v1/meetings")
        response = httpx.Response(503, request=request)
        f1_fail = AsyncMock(
            side_effect=httpx.HTTPStatusError("503", request=request, response=response)
        )
        with (
            patch.object(OpenF1Source, "_get_json", f1_fail),
            patch.object(OfficialWecSource, "get_season", _mock_wec(_WEC_EVENTS)),
        ):
            result = runner.invoke(app, ["generate", "2024", str(tmp_path / "all.ics")])
        assert result.exit_code == 0

    def test_f1_timeout_wec_succeeds_exits_zero(self, tmp_path: Path) -> None:
        request = httpx.Request("GET", "https://api.openf1.org/v1/meetings")
        f1_timeout = AsyncMock(side_effect=httpx.TimeoutException("timeout", request=request))
        with (
            patch.object(OpenF1Source, "_get_json", f1_timeout),
            patch.object(OfficialWecSource, "get_season", _mock_wec(_WEC_EVENTS)),
        ):
            result = runner.invoke(app, ["generate", "2024", str(tmp_path / "all.ics")])
        assert result.exit_code == 0

    def test_surviving_provider_events_exported_when_one_fails(self, tmp_path: Path) -> None:
        output = tmp_path / "all.ics"
        request = httpx.Request("GET", "https://api.openf1.org/v1/meetings")
        response = httpx.Response(503, request=request)
        f1_fail = AsyncMock(
            side_effect=httpx.HTTPStatusError("503", request=request, response=response)
        )
        _empty = AsyncMock(return_value={"races": []})
        with (
            patch.object(OpenF1Source, "_get_json", f1_fail),
            patch.object(OfficialWecSource, "get_season", _mock_wec(_WEC_EVENTS)),
            patch.object(F2CalendarSource, "fetch_json", _empty),
            patch.object(F3CalendarSource, "fetch_json", _empty),
            patch.object(F1AcademyCalendarSource, "fetch_json", _empty),
        ):
            runner.invoke(app, ["generate", "2024", str(output)])
        content = output.read_text(encoding="utf-8")
        assert content.count("BEGIN:VEVENT") == _WEC_SESSION_COUNT


# ---------------------------------------------------------------------------
# --refresh flag
# ---------------------------------------------------------------------------


class TestGenerateRefresh:
    def test_refresh_flag_exits_zero(self, tmp_path: Path) -> None:
        with patch.object(OpenF1Source, "_get_json", _mock_f1(_F1_MEETINGS, _F1_SESSIONS)):
            result = runner.invoke(
                app, ["generate", "2024", str(tmp_path / "all.ics"), "--refresh"]
            )
        assert result.exit_code == 0

    def test_refresh_flag_creates_file(self, tmp_path: Path) -> None:
        output = tmp_path / "all-refresh.ics"
        with patch.object(OpenF1Source, "_get_json", _mock_f1(_F1_MEETINGS, _F1_SESSIONS)):
            runner.invoke(app, ["generate", "2024", str(output), "--refresh"])
        assert output.exists()


# ---------------------------------------------------------------------------
# Tri chronologique
# ---------------------------------------------------------------------------


class TestGenerateSorting:
    def test_events_sorted_chronologically(self, tmp_path: Path) -> None:
        """Les events WEC de janvier doivent apparaître avant les events F1 de mars."""
        output = tmp_path / "sorted.ics"
        with (
            patch.object(OpenF1Source, "_get_json", _mock_f1(_F1_MEETINGS, _F1_SESSIONS)),
            patch.object(OfficialWecSource, "get_season", _mock_wec(_WEC_EVENTS_EARLY)),
        ):
            runner.invoke(app, ["generate", "2024", str(output)])

        content = output.read_text(encoding="utf-8")
        vevents = content.split("BEGIN:VEVENT")
        # vevents[0] = header VCALENDAR, vevents[1] = premier VEVENT
        assert len(vevents) >= 2
        # Le premier VEVENT doit être Daytona (janvier 2024 → 20240127)
        assert "20240127" in vevents[1]


# ---------------------------------------------------------------------------
# Concurrence (Sprint 50) — chaque provider est indépendant (API distante
# différente) ; les récupérer en parallèle (asyncio.gather) plutôt que
# séquentiellement réduit le temps total au provider le plus lent, pas à leur
# somme. Mesuré ici plutôt qu'affirmé, conformément au brief Sprint 50
# ("ne réaliser une optimisation que si elle est mesurable").
# ---------------------------------------------------------------------------


class TestGenerateConcurrency:
    def test_providers_are_fetched_concurrently_not_sequentially(self, tmp_path: Path) -> None:
        """Records each mocked provider call's *start* timestamp rather than
        asserting a wall-clock budget for the whole CLI invocation: registry
        discovery (importing all 17 provider packages) and provider/source
        construction happen before ``asyncio.gather`` and take far longer
        than the artificial delay below, so a total-elapsed-time assertion
        would just measure that unrelated, pre-existing overhead. What
        Sprint 50 actually changed is that every provider's own fetch call
        starts at (approximately) the same instant instead of one starting
        only after the previous one finished — that spread is what's
        measured here.
        """
        import time

        delay = 0.05
        start_times: list[float] = []

        async def _record_start_then_sleep() -> None:
            start_times.append(time.perf_counter())
            await asyncio.sleep(delay)

        async def _slow_json(*args: object, **kwargs: object) -> dict[str, list]:
            await _record_start_then_sleep()
            return {"races": []}

        async def _slow_html(*args: object, **kwargs: object) -> str:
            await _record_start_then_sleep()
            return "<html><body>no races</body></html>"

        async def _slow_moto(*args: object, **kwargs: object) -> list:
            await _record_start_then_sleep()
            return []

        async def _slow_wec(*args: object, **kwargs: object) -> list:
            await _record_start_then_sleep()
            return []

        with (
            patch.object(OpenF1Source, "_get_json", _mock_f1(_F1_MEETINGS, _F1_SESSIONS)),
            patch.object(F2CalendarSource, "fetch_json", _slow_json),
            patch.object(F3CalendarSource, "fetch_json", _slow_json),
            patch.object(F1AcademyCalendarSource, "fetch_json", _slow_json),
            patch.object(FormulaECalendarSource, "fetch_json", _slow_json),
            patch.object(ElmsAcoScraperSource, "fetch_html", _slow_html),
            patch.object(MlmcAcoScraperSource, "fetch_html", _slow_html),
            patch.object(GtwcEuropeSroScraperSource, "fetch_html", _slow_html),
            patch.object(GtwcAmericaSroScraperSource, "fetch_html", _slow_html),
            patch.object(GtwcAsiaSroScraperSource, "fetch_html", _slow_html),
            patch.object(IgtcSroScraperSource, "fetch_html", _slow_html),
            patch.object(MotoGpPulseliveSource, "fetch_json", _slow_moto),
            patch.object(Moto2PulseliveSource, "fetch_json", _slow_moto),
            patch.object(Moto3PulseliveSource, "fetch_json", _slow_moto),
            patch.object(OfficialWecSource, "get_season", _slow_wec),
        ):
            result = runner.invoke(app, ["generate", "2024", str(tmp_path / "all.ics")])

        assert result.exit_code == 0
        assert len(start_times) == 14  # every mocked provider was actually called
        # Concurrent: all 14 calls start within one delay window of each
        # other. Sequential (the pre-Sprint-50 behaviour) would spread them
        # out by ~13 * delay (~0.65s) since each awaits the previous one's
        # full sleep before starting.
        spread = max(start_times) - min(start_times)
        assert spread < delay, (
            f"provider fetch calls spread over {spread:.3f}s — "
            f"expected concurrent start within {delay}s"
        )
