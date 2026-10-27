"""Tests for GUI controller — no Flet dependency, mocked HTTP."""

from __future__ import annotations

import asyncio
from contextlib import ExitStack, contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx

from motorsport_calendar.gui.controller import (
    check_for_update,
    generate_calendar,
    get_calendar_year_events,
    get_dashboard_data,
    get_upcoming_weekend,
    list_championships,
    prepare_notifications,
)
from motorsport_calendar.models import (
    Championship,
    ChampionshipCategory,
    Circuit,
    Event,
    Session,
    SessionType,
)

# ---------------------------------------------------------------------------
# Minimal F2 fixture — 1 event, 4 sessions (2024 keys)
# ---------------------------------------------------------------------------

_F2_ONE_RACE = {
    "name": "Formula 2",
    "races": [
        {
            "name": "Bahrain Grand Prix",
            "location": "Sakhir",
            "round": 1,
            "slug": "bahrain",
            "localeKey": "bahrain",
            "sessions": {
                "fp1": "2024-02-29T11:05:00Z",
                "qualifying": "2024-03-01T12:10:00Z",
                "sprintRace": "2024-03-02T09:05:00Z",
                "feature": "2024-03-03T10:05:00Z",
            },
        }
    ],
}

_F2_EMPTY = {"name": "Formula 2", "races": []}


# ---------------------------------------------------------------------------
# TestListChampionships
# ---------------------------------------------------------------------------


class TestListChampionships:
    def test_returns_a_list(self) -> None:
        assert isinstance(list_championships(), list)

    def test_is_sorted(self) -> None:
        result = list_championships()
        assert result == sorted(result)

    def test_contains_formula1(self) -> None:
        assert "formula1" in list_championships()

    def test_contains_formula2(self) -> None:
        assert "formula2" in list_championships()

    def test_contains_formula3(self) -> None:
        assert "formula3" in list_championships()

    def test_contains_f1_academy(self) -> None:
        assert "f1-academy" in list_championships()

    def test_contains_wec(self) -> None:
        assert "wec" in list_championships()

    def test_idempotent(self) -> None:
        assert list_championships() == list_championships()

    def test_imsa_hidden_from_the_gui(self) -> None:
        """Sprint 57 (Préparation Beta — positionnement) — IMSA has no
        reliable source yet, so it is no longer proposed to the user."""
        assert "imsa" not in list_championships()

    def test_worldsbk_hidden_from_the_gui(self) -> None:
        assert "worldsbk" not in list_championships()

    def test_imsa_and_worldsbk_remain_fully_registered_in_the_architecture(self) -> None:
        """ "Aucune suppression de code" — hiding from the GUI's own
        picker must never touch ``ProviderRegistry`` itself; both
        providers stay discoverable/generatable via the CLI."""
        from motorsport_calendar.core.registry import registry

        registry.discover()
        assert "imsa" in registry.list_all()
        assert "worldsbk" in registry.list_all()


# ---------------------------------------------------------------------------
# TestGenerateCalendarEmptySelection
# ---------------------------------------------------------------------------


class TestGenerateCalendarEmptySelection:
    async def test_empty_ids_returns_empty_dict(self, tmp_path: Path) -> None:
        result = await generate_calendar(
            year=2025,
            championship_ids=[],
            output_path=str(tmp_path / "out.ics"),
        )
        assert result == {}

    async def test_no_ics_file_created_for_empty_selection(self, tmp_path: Path) -> None:
        output = tmp_path / "out.ics"
        await generate_calendar(year=2025, championship_ids=[], output_path=str(output))
        assert not output.exists()


# ---------------------------------------------------------------------------
# TestGenerateCalendarImsa — NotImplementedError path
#
# Sprint 48: WEC's OfficialWecSource is now a real implementation
# (fiawec.com JSON-LD) — this class used to be TestGenerateCalendarWec,
# demonstrating generate_calendar's handling of a genuinely unimplemented
# source via WEC's own real (unmocked) NotImplementedError. IMSA remains a
# real stub (no viable data source found, see docs/DATA_SOURCES.md) and
# now plays that same role — same test intent, same assertions, only the
# championship id changed.
# ---------------------------------------------------------------------------


class TestGenerateCalendarImsa:
    async def test_not_implemented_source_returns_error_string(self, tmp_path: Path) -> None:
        result = await generate_calendar(
            year=2025,
            championship_ids=["imsa"],
            output_path=str(tmp_path / "out.ics"),
        )
        assert "imsa" in result
        assert isinstance(result["imsa"], str)

    async def test_error_string_contains_useful_text(self, tmp_path: Path) -> None:
        result = await generate_calendar(
            year=2025,
            championship_ids=["imsa"],
            output_path=str(tmp_path / "out.ics"),
        )
        msg = result["imsa"]
        assert isinstance(msg, str) and len(msg) > 0


# ---------------------------------------------------------------------------
# TestGenerateCalendarFormula2 — happy path
# ---------------------------------------------------------------------------


class TestGenerateCalendarFormula2:
    async def test_zero_events_returns_count_zero(self, tmp_path: Path) -> None:
        from motorsport_calendar.providers.formula2.sources.f1calendar import (
            F1CalendarSource as F2Source,
        )

        with patch.object(F2Source, "fetch_json", AsyncMock(return_value=_F2_EMPTY)):
            result = await generate_calendar(
                year=2025,
                championship_ids=["formula2"],
                output_path=str(tmp_path / "out.ics"),
            )
        assert result.get("formula2") == (0, 0)

    async def test_zero_events_produces_no_file(self, tmp_path: Path) -> None:
        from motorsport_calendar.providers.formula2.sources.f1calendar import (
            F1CalendarSource as F2Source,
        )

        output = tmp_path / "out.ics"
        with patch.object(F2Source, "fetch_json", AsyncMock(return_value=_F2_EMPTY)):
            await generate_calendar(
                year=2025,
                championship_ids=["formula2"],
                output_path=str(output),
            )
        assert not output.exists()

    async def test_one_event_returns_count_one(self, tmp_path: Path) -> None:
        from motorsport_calendar.providers.formula2.sources.f1calendar import (
            F1CalendarSource as F2Source,
        )

        with patch.object(F2Source, "fetch_json", AsyncMock(return_value=_F2_ONE_RACE)):
            result = await generate_calendar(
                year=2024,
                championship_ids=["formula2"],
                output_path=str(tmp_path / "out.ics"),
            )
        # _F2_ONE_RACE has 1 event with 4 sessions (fp1, qualifying, sprintRace, feature)
        assert result.get("formula2") == (1, 4)

    async def test_one_event_creates_ics_file(self, tmp_path: Path) -> None:
        from motorsport_calendar.providers.formula2.sources.f1calendar import (
            F1CalendarSource as F2Source,
        )

        output = tmp_path / "out.ics"
        with patch.object(F2Source, "fetch_json", AsyncMock(return_value=_F2_ONE_RACE)):
            await generate_calendar(
                year=2024,
                championship_ids=["formula2"],
                output_path=str(output),
            )
        assert output.exists()
        assert "BEGIN:VCALENDAR" in output.read_text(encoding="utf-8")

    async def test_ics_contains_correct_vevent_count(self, tmp_path: Path) -> None:
        from motorsport_calendar.providers.formula2.sources.f1calendar import (
            F1CalendarSource as F2Source,
        )

        output = tmp_path / "out.ics"
        with patch.object(F2Source, "fetch_json", AsyncMock(return_value=_F2_ONE_RACE)):
            await generate_calendar(
                year=2024,
                championship_ids=["formula2"],
                output_path=str(output),
            )
        content = output.read_text(encoding="utf-8")
        # 1 event x 4 sessions = 4 VEVENTs
        assert content.count("BEGIN:VEVENT") == 4


# ---------------------------------------------------------------------------
# TestGenerateCalendarIcsAlarmMinutes (Sprint 52 — "rappel avant export")
# ---------------------------------------------------------------------------


class TestGenerateCalendarIcsAlarmMinutes:
    async def test_default_preference_matches_config_default(self, tmp_path: Path) -> None:
        """No preference ever saved (fresh install) — falls back to
        config.ics.alarm_minutes (30), byte-identical to pre-Sprint-52
        behaviour."""
        from motorsport_calendar.providers.formula2.sources.f1calendar import (
            F1CalendarSource as F2Source,
        )

        output = tmp_path / "out.ics"
        with patch.object(F2Source, "fetch_json", AsyncMock(return_value=_F2_ONE_RACE)):
            await generate_calendar(
                year=2024,
                championship_ids=["formula2"],
                output_path=str(output),
            )
        assert "TRIGGER:-PT30M" in output.read_text(encoding="utf-8")

    async def test_preference_overrides_config_default(self, tmp_path: Path) -> None:
        from motorsport_calendar.gui.preferences import load_preferences, save_preferences
        from motorsport_calendar.providers.formula2.sources.f1calendar import (
            F1CalendarSource as F2Source,
        )

        prefs = load_preferences()
        prefs["ics_alarm_minutes"] = 15
        save_preferences(prefs)

        output = tmp_path / "out.ics"
        with patch.object(F2Source, "fetch_json", AsyncMock(return_value=_F2_ONE_RACE)):
            await generate_calendar(
                year=2024,
                championship_ids=["formula2"],
                output_path=str(output),
            )
        content = output.read_text(encoding="utf-8")
        assert "TRIGGER:-PT15M" in content
        assert "TRIGGER:-PT30M" not in content

    async def test_preference_zero_disables_the_alarm_entirely(self, tmp_path: Path) -> None:
        from motorsport_calendar.gui.preferences import load_preferences, save_preferences
        from motorsport_calendar.providers.formula2.sources.f1calendar import (
            F1CalendarSource as F2Source,
        )

        prefs = load_preferences()
        prefs["ics_alarm_minutes"] = 0
        save_preferences(prefs)

        output = tmp_path / "out.ics"
        with patch.object(F2Source, "fetch_json", AsyncMock(return_value=_F2_ONE_RACE)):
            await generate_calendar(
                year=2024,
                championship_ids=["formula2"],
                output_path=str(output),
            )
        assert "BEGIN:VALARM" not in output.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# TestGenerateCalendarErrors
# ---------------------------------------------------------------------------


class TestGenerateCalendarErrors:
    async def test_http_404_returns_error_string(self, tmp_path: Path) -> None:
        from motorsport_calendar.providers.formula2.sources.f1calendar import (
            F1CalendarSource as F2Source,
        )

        request = httpx.Request("GET", "https://example.com")
        response = httpx.Response(404, request=request)
        exc = httpx.HTTPStatusError("HTTP 404", request=request, response=response)

        with patch.object(F2Source, "fetch_json", AsyncMock(side_effect=exc)):
            result = await generate_calendar(
                year=2025,
                championship_ids=["formula2"],
                output_path=str(tmp_path / "out.ics"),
            )
        assert "404" in str(result.get("formula2"))

    async def test_timeout_returns_timeout_string(self, tmp_path: Path) -> None:
        from motorsport_calendar.providers.formula2.sources.f1calendar import (
            F1CalendarSource as F2Source,
        )

        with patch.object(
            F2Source, "fetch_json", AsyncMock(side_effect=httpx.TimeoutException("timeout"))
        ):
            result = await generate_calendar(
                year=2025,
                championship_ids=["formula2"],
                output_path=str(tmp_path / "out.ics"),
            )
        assert "timeout" in str(result.get("formula2")).lower()

    async def test_partial_failure_still_exports_successful(self, tmp_path: Path) -> None:
        """IMSA fails (NotImplementedError, real stub) but F2 succeeds → ICS
        file still created."""
        from motorsport_calendar.providers.formula2.sources.f1calendar import (
            F1CalendarSource as F2Source,
        )

        output = tmp_path / "out.ics"
        with patch.object(F2Source, "fetch_json", AsyncMock(return_value=_F2_ONE_RACE)):
            result = await generate_calendar(
                year=2024,
                championship_ids=["formula2", "imsa"],
                output_path=str(output),
            )
        assert isinstance(result.get("formula2"), tuple)
        assert isinstance(result.get("imsa"), str)
        assert output.exists()


# ---------------------------------------------------------------------------
# TestGenerateCalendarConcurrency (Sprint 50)
# ---------------------------------------------------------------------------


class TestGenerateCalendarConcurrency:
    async def test_providers_are_fetched_concurrently_not_sequentially(
        self, tmp_path: Path
    ) -> None:
        """Same measurement strategy as
        test_cli_generate.py::TestGenerateConcurrency — records each mocked
        provider's fetch *start* timestamp rather than asserting a
        wall-clock budget, since ``generate_calendar`` also runs
        ``registry.discover()``/``source_registry.discover()`` internally
        (import overhead unrelated to the concurrency fix itself)."""
        import time

        from motorsport_calendar.providers.f1_academy.sources.f1calendar import (
            F1CalendarSource as F1AcademySource,
        )
        from motorsport_calendar.providers.formula2.sources.f1calendar import (
            F1CalendarSource as F2Source,
        )
        from motorsport_calendar.providers.formula3.sources.f1calendar import (
            F1CalendarSource as F3Source,
        )
        from motorsport_calendar.providers.formula_e.sources.f1calendar import (
            F1CalendarSource as FormulaESource,
        )

        delay = 0.05
        start_times: list[float] = []

        async def _slow_json(*args: object, **kwargs: object) -> dict[str, list]:
            start_times.append(time.perf_counter())
            await asyncio.sleep(delay)
            return {"races": []}

        with (
            patch.object(F2Source, "fetch_json", _slow_json),
            patch.object(F3Source, "fetch_json", _slow_json),
            patch.object(F1AcademySource, "fetch_json", _slow_json),
            patch.object(FormulaESource, "fetch_json", _slow_json),
        ):
            result = await generate_calendar(
                year=2025,
                championship_ids=["formula2", "formula3", "f1-academy", "formula-e"],
                output_path=str(tmp_path / "out.ics"),
            )

        assert all(result[cid] == (0, 0) for cid in result)
        assert len(start_times) == 4
        spread = max(start_times) - min(start_times)
        assert spread < delay, (
            f"provider fetch calls spread over {spread:.3f}s — "
            f"expected concurrent start within {delay}s"
        )


# ---------------------------------------------------------------------------
# TestGetUpcomingWeekend
# ---------------------------------------------------------------------------

# Non-IMSA/WorldSBK "Ce week-end" sources, one per championship — mocked at
# the get_season() level (Provider.fetch_events delegates straight to it),
# so no raw JSON fixtures are needed. IMSA/WorldSBK's sources always raise
# NotImplementedError for real (no viable data source found — see
# docs/DATA_SOURCES.md) — no mock required, matches production. WEC's
# OfficialWecSource is a real implementation since Sprint 48, mocked here
# exactly like every other real source.
_WEEKEND_SOURCE_PATHS = {
    # ProvidersConfig defaults formula1 to the "openf1" source (see
    # config/models.py) — not the first-registered "jolpica" — mock that
    # one to match what get_upcoming_weekend actually calls.
    "formula1": "motorsport_calendar.providers.formula1.sources.openf1.OpenF1Source.get_season",
    "formula2": (
        "motorsport_calendar.providers.formula2.sources.f1calendar.F1CalendarSource.get_season"
    ),
    "formula3": (
        "motorsport_calendar.providers.formula3.sources.f1calendar.F1CalendarSource.get_season"
    ),
    "f1-academy": (
        "motorsport_calendar.providers.f1_academy.sources.f1calendar.F1CalendarSource.get_season"
    ),
    "formula-e": (
        "motorsport_calendar.providers.formula_e.sources.f1calendar.F1CalendarSource.get_season"
    ),
    "elms": ("motorsport_calendar.providers.elms.sources.aco_scraper.AcoScraperSource.get_season"),
    "mlmc": ("motorsport_calendar.providers.mlmc.sources.aco_scraper.AcoScraperSource.get_season"),
    "gtwc-europe": (
        "motorsport_calendar.providers.gtwc_europe.sources.sro_scraper.SroScraperSource.get_season"
    ),
    "gtwc-america": (
        "motorsport_calendar.providers.gtwc_america.sources.sro_scraper.SroScraperSource.get_season"
    ),
    "gtwc-asia": (
        "motorsport_calendar.providers.gtwc_asia.sources.sro_scraper.SroScraperSource.get_season"
    ),
    "igtc": ("motorsport_calendar.providers.igtc.sources.sro_scraper.SroScraperSource.get_season"),
    "motogp": ("motorsport_calendar.providers.motogp.sources.pulselive.PulseliveSource.get_season"),
    "moto2": ("motorsport_calendar.providers.moto2.sources.pulselive.PulseliveSource.get_season"),
    "moto3": ("motorsport_calendar.providers.moto3.sources.pulselive.PulseliveSource.get_season"),
    "wec": "motorsport_calendar.providers.wec.sources.official.OfficialWecSource.get_season",
}


@contextmanager
def patch_weekend_sources(events_by_championship: dict[str, list[Event]] | None = None):
    """Patch get_season() for the 15 non-IMSA/WorldSBK weekend championships.

    Each championship is fetched for 2 years (now.year and now.year + 1) —
    the mock only returns events whose season matches the requested year,
    so a fixture built for one year doesn't get double-counted on the
    second fetch call.
    """
    events_by_championship = events_by_championship or {}

    def _get_season_for(cid: str):
        async def _get_season(year: int) -> list[Event]:
            return [e for e in events_by_championship.get(cid, []) if e.season == year]

        return _get_season

    with ExitStack() as stack:
        for cid, target in _WEEKEND_SOURCE_PATHS.items():
            stack.enter_context(patch(target, side_effect=_get_season_for(cid)))
        yield


def _weekend_session(session_type: SessionType, start: datetime) -> Session:
    return Session(
        type=session_type,
        start_datetime=start,
        end_datetime=start + timedelta(hours=1),
        title=session_type.value,
    )


def _weekend_event(championship_id: str, *, start: datetime) -> Event:
    championship = Championship(
        id=championship_id, name=championship_id, category=ChampionshipCategory.SINGLE_SEATER
    )
    circuit = Circuit(
        id="test-circuit",
        name="Test Circuit",
        city="Test",
        country="France",
        timezone="Europe/Paris",
    )
    return Event(
        championship=championship,
        season=start.year,
        round=1,
        name="Test Grand Prix",
        circuit=circuit,
        sessions=(_weekend_session(SessionType.RACE, start),),
        event_uid=f"{championship_id}-1@test",
    )


# A Tuesday — the upcoming weekend is Friday 2026-07-10 to Sunday 2026-07-12.
_WEEKEND_NOW = datetime(2026, 7, 7, 12, 0, tzinfo=UTC)


class TestGetUpcomingWeekend:
    async def test_no_data_anywhere_returns_not_found(self) -> None:
        with patch_weekend_sources():
            result = await get_upcoming_weekend(now=_WEEKEND_NOW)
        assert result.found is False

    async def test_formula1_event_this_weekend_is_found(self) -> None:
        event = _weekend_event("formula1", start=datetime(2026, 7, 12, 13, 0, tzinfo=UTC))
        with patch_weekend_sources({"formula1": [event]}):
            result = await get_upcoming_weekend(now=_WEEKEND_NOW)
        assert result.found is True
        assert len(result.cards) == 1
        assert result.cards[0].championship_id == "formula1"

    async def test_imsa_worldsbk_not_implemented_does_not_crash_the_whole_call(self) -> None:
        """IMSA/WorldSBK's real sources always raise NotImplementedError —
        the other 15 championships must still be attempted and the call
        must not raise."""
        with patch_weekend_sources():
            result = await get_upcoming_weekend(now=_WEEKEND_NOW)
        assert result.found is False  # nothing mocked in — but no crash

    async def test_partial_provider_failure_does_not_crash(self) -> None:
        event = _weekend_event("formula2", start=datetime(2026, 7, 11, 9, 0, tzinfo=UTC))
        with ExitStack() as stack:
            stack.enter_context(
                patch(
                    _WEEKEND_SOURCE_PATHS["formula1"],
                    AsyncMock(side_effect=httpx.TimeoutException("timeout")),
                )
            )
            stack.enter_context(
                patch(_WEEKEND_SOURCE_PATHS["formula2"], AsyncMock(return_value=[event]))
            )
            stack.enter_context(
                patch(_WEEKEND_SOURCE_PATHS["formula3"], AsyncMock(return_value=[]))
            )
            stack.enter_context(
                patch(_WEEKEND_SOURCE_PATHS["f1-academy"], AsyncMock(return_value=[]))
            )
            stack.enter_context(
                patch(_WEEKEND_SOURCE_PATHS["formula-e"], AsyncMock(return_value=[]))
            )
            stack.enter_context(patch(_WEEKEND_SOURCE_PATHS["elms"], AsyncMock(return_value=[])))
            stack.enter_context(patch(_WEEKEND_SOURCE_PATHS["mlmc"], AsyncMock(return_value=[])))
            stack.enter_context(
                patch(_WEEKEND_SOURCE_PATHS["gtwc-europe"], AsyncMock(return_value=[]))
            )
            stack.enter_context(
                patch(_WEEKEND_SOURCE_PATHS["gtwc-america"], AsyncMock(return_value=[]))
            )
            stack.enter_context(
                patch(_WEEKEND_SOURCE_PATHS["gtwc-asia"], AsyncMock(return_value=[]))
            )
            stack.enter_context(patch(_WEEKEND_SOURCE_PATHS["igtc"], AsyncMock(return_value=[])))
            stack.enter_context(patch(_WEEKEND_SOURCE_PATHS["motogp"], AsyncMock(return_value=[])))
            stack.enter_context(patch(_WEEKEND_SOURCE_PATHS["moto2"], AsyncMock(return_value=[])))
            stack.enter_context(patch(_WEEKEND_SOURCE_PATHS["moto3"], AsyncMock(return_value=[])))
            result = await get_upcoming_weekend(now=_WEEKEND_NOW)
        assert result.found is True
        assert result.cards[0].championship_id == "formula2"

    async def test_now_override_controls_which_weekend_is_searched(self) -> None:
        event = _weekend_event("formula1", start=datetime(2026, 8, 15, 13, 0, tzinfo=UTC))
        with patch_weekend_sources({"formula1": [event]}):
            result = await get_upcoming_weekend(now=_WEEKEND_NOW)
        assert result.found is True
        assert result.friday.isoformat() == "2026-08-14"
        assert result.sunday.isoformat() == "2026-08-16"

    async def test_default_now_is_used_when_omitted(self) -> None:
        """Calling without `now` must not raise — it defaults to the real
        current time internally. With every source mocked empty, there is
        nothing to find regardless of what "now" resolves to."""
        with patch_weekend_sources():
            result = await get_upcoming_weekend()
        assert result.found is False

    async def test_championship_with_no_registered_source_is_skipped(self) -> None:
        from motorsport_calendar.core.source_registry import source_registry

        with (
            patch_weekend_sources(),
            patch.object(source_registry, "list_for", return_value=[]),
        ):
            result = await get_upcoming_weekend(now=_WEEKEND_NOW)
        assert result.found is False

    async def test_championship_with_unregistered_provider_is_skipped(self) -> None:
        from motorsport_calendar.core.registry import registry

        with patch_weekend_sources(), patch.object(registry, "get", side_effect=KeyError("x")):
            result = await get_upcoming_weekend(now=_WEEKEND_NOW)
        assert result.found is False

    async def test_favorited_championship_appears_first(self) -> None:
        """Sprint 44 — get_upcoming_weekend reads FavoritesService itself,
        so a favorite saved by "Mes favoris" is reflected here without any
        extra plumbing at the call site."""
        from motorsport_calendar.gui.favorites_service import FavoritesService

        # Without favorites, formula2's earlier session already puts it
        # first (chronological order within the same category) — favorite
        # formula1 (the naturally-second one) to prove the override
        # actually happened, not a coincidence of the existing order.
        f1 = _weekend_event("formula1", start=datetime(2026, 7, 12, 13, 0, tzinfo=UTC))
        f2 = _weekend_event("formula2", start=datetime(2026, 7, 11, 8, 0, tzinfo=UTC))
        FavoritesService().add("formula1")
        with patch_weekend_sources({"formula1": [f1], "formula2": [f2]}):
            result = await get_upcoming_weekend(now=_WEEKEND_NOW)
        assert [card.championship_id for card in result.cards] == ["formula1", "formula2"]

    async def test_no_favorites_leaves_the_existing_order_unchanged(self) -> None:
        f1 = _weekend_event("formula1", start=datetime(2026, 7, 12, 13, 0, tzinfo=UTC))
        f2 = _weekend_event("formula2", start=datetime(2026, 7, 11, 8, 0, tzinfo=UTC))
        with patch_weekend_sources({"formula1": [f1], "formula2": [f2]}):
            result = await get_upcoming_weekend(now=_WEEKEND_NOW)
        # f2's earlier session wins within the same category (chronological
        # order), same as TestChronologicalOrderWithinCategory.
        assert [card.championship_id for card in result.cards] == ["formula2", "formula1"]

    async def test_refresh_flag_forwarded_to_every_source_constructed(self) -> None:
        """MC-002 (P0-7): get_upcoming_weekend(refresh=True) — via the
        shared _fetch_weekend_entries — must bypass the HTTP cache for
        every championship it fetches, not just some. Spies on
        source_registry.get (returns the (cache, refresh) -> Source
        factory _resolve_source_and_provider_factories calls) rather than
        the Source constructors themselves, since those differ per
        championship."""
        from motorsport_calendar.core.source_registry import source_registry

        real_get = source_registry.get
        captured_refresh: list[bool] = []

        def _spy_get(cid: str, source_name: str):
            real_factory = real_get(cid, source_name)

            def _wrapped(cache: object, refresh: bool):
                captured_refresh.append(refresh)
                return real_factory(cache, refresh)

            return _wrapped

        with (
            patch_weekend_sources(),
            patch.object(source_registry, "get", side_effect=_spy_get),
        ):
            await get_upcoming_weekend(now=_WEEKEND_NOW, refresh=True)

        assert captured_refresh  # at least one source was actually constructed
        assert all(captured_refresh)

    async def test_refresh_defaults_to_false(self) -> None:
        from motorsport_calendar.core.source_registry import source_registry

        real_get = source_registry.get
        captured_refresh: list[bool] = []

        def _spy_get(cid: str, source_name: str):
            real_factory = real_get(cid, source_name)

            def _wrapped(cache: object, refresh: bool):
                captured_refresh.append(refresh)
                return real_factory(cache, refresh)

            return _wrapped

        with (
            patch_weekend_sources(),
            patch.object(source_registry, "get", side_effect=_spy_get),
        ):
            await get_upcoming_weekend(now=_WEEKEND_NOW)

        assert captured_refresh
        assert not any(captured_refresh)


# ---------------------------------------------------------------------------
# TestGetDashboardData (Sprint 39)
# ---------------------------------------------------------------------------


class TestGetDashboardData:
    async def test_no_data_anywhere_returns_zero_counts_and_no_weekend(self) -> None:
        with patch_weekend_sources():
            data = await get_dashboard_data(now=_WEEKEND_NOW)
        assert data.total_events_season == 0
        assert data.total_sessions_season == 0
        assert data.weekend.found is False
        assert data.next_race is None

    async def test_total_championships_matches_registry(self) -> None:
        from motorsport_calendar.core.registry import registry

        registry.discover()
        expected = len(registry.list_all())
        with patch_weekend_sources():
            data = await get_dashboard_data(now=_WEEKEND_NOW)
        assert data.total_championships == expected

    async def test_formula1_event_this_weekend_is_reflected_in_weekend_and_next_race(
        self,
    ) -> None:
        event = _weekend_event("formula1", start=datetime(2026, 7, 12, 13, 0, tzinfo=UTC))
        with patch_weekend_sources({"formula1": [event]}):
            data = await get_dashboard_data(now=_WEEKEND_NOW)
        assert data.weekend.found is True
        assert len(data.weekend.cards) == 1
        assert data.next_race is not None
        assert data.total_events_season == 1
        assert data.total_sessions_season == 1

    async def test_partial_provider_failure_does_not_crash(self) -> None:
        """formula1 fails outright — the dashboard must still aggregate
        whatever the surviving providers returned, exactly like "Ce
        week-end" does (same shared fetch pipeline, see
        controller._fetch_weekend_entries).
        """
        event = _weekend_event("formula2", start=datetime(2026, 7, 11, 9, 0, tzinfo=UTC))
        with (
            patch_weekend_sources({"formula2": [event]}),
            patch(
                _WEEKEND_SOURCE_PATHS["formula1"],
                AsyncMock(side_effect=httpx.TimeoutException("timeout")),
            ),
        ):
            data = await get_dashboard_data(now=_WEEKEND_NOW)
        assert data.weekend.found is True
        assert data.total_events_season == 1

    async def test_default_now_is_used_when_omitted(self) -> None:
        with patch_weekend_sources():
            data = await get_dashboard_data()
        assert data.weekend.found is False
        assert data.total_events_season == 0

    async def test_favorited_championship_appears_first_in_weekend_cards(self) -> None:
        """Sprint 44 — same FavoritesService-reading behavior as
        get_upcoming_weekend, since both share find_upcoming_weekend."""
        from motorsport_calendar.gui.favorites_service import FavoritesService

        f1 = _weekend_event("formula1", start=datetime(2026, 7, 12, 13, 0, tzinfo=UTC))
        f2 = _weekend_event("formula2", start=datetime(2026, 7, 11, 8, 0, tzinfo=UTC))
        FavoritesService().add("formula1")
        with patch_weekend_sources({"formula1": [f1], "formula2": [f2]}):
            data = await get_dashboard_data(now=_WEEKEND_NOW)
        assert [card.championship_id for card in data.weekend.cards] == ["formula1", "formula2"]

    async def test_refresh_flag_accepted_and_forwarded(self) -> None:
        """MC-002 (P0-7) — shares _fetch_weekend_entries with
        get_upcoming_weekend (TestGetUpcomingWeekend has the deep
        source-factory-forwarding proof); this only confirms the
        parameter reaches that shared call without breaking anything
        dashboard-specific (the concurrent check_for_update() gather)."""
        with patch_weekend_sources():
            data = await get_dashboard_data(now=_WEEKEND_NOW, refresh=True)
        assert data.total_events_season == 0


# ---------------------------------------------------------------------------
# TestGetCalendarYearEvents (Sprint 40 — "Mon calendrier" navigateur)
# ---------------------------------------------------------------------------


class TestGetCalendarYearEvents:
    async def test_no_data_anywhere_returns_empty_lists_for_every_fetched_championship(
        self,
    ) -> None:
        """A successful fetch with zero matching events still yields an
        entry — an empty list, not a missing key. Only a *failed* fetch
        (exception) omits the championship (see the IMSA/WorldSBK
        NotImplementedError case below)."""
        with patch_weekend_sources():
            result = await get_calendar_year_events(2026)
        assert result["formula1"] == []

    async def test_only_requested_year_is_fetched_no_lookahead(self) -> None:
        """Unlike _fetch_weekend_entries, this is scoped to exactly one
        year — no year+1 lookahead."""
        event_2026 = _weekend_event("formula1", start=datetime(2026, 3, 1, 13, 0, tzinfo=UTC))
        event_2027 = _weekend_event("formula1", start=datetime(2027, 3, 1, 13, 0, tzinfo=UTC))
        with patch_weekend_sources({"formula1": [event_2026, event_2027]}):
            result = await get_calendar_year_events(2026)
        assert [e.season for e in result["formula1"]] == [2026]

    async def test_fetched_events_keyed_by_championship_id(self) -> None:
        event = _weekend_event("formula1", start=datetime(2026, 3, 1, 13, 0, tzinfo=UTC))
        with patch_weekend_sources({"formula1": [event]}):
            result = await get_calendar_year_events(2026)
        assert result["formula1"] == [event]

    async def test_championship_with_no_events_for_year_has_empty_list(self) -> None:
        with patch_weekend_sources():
            result = await get_calendar_year_events(2026)
        assert result["formula1"] == []

    async def test_imsa_worldsbk_not_implemented_does_not_crash_the_whole_call(self) -> None:
        """IMSA/WorldSBK's real sources always raise NotImplementedError —
        unlike _fetch_weekend_entries, get_calendar_year_events covers every
        registered championship (not just the 15-championship weekend
        subset), so these two must be tolerated too."""
        event = _weekend_event("formula1", start=datetime(2026, 3, 1, 13, 0, tzinfo=UTC))
        with patch_weekend_sources({"formula1": [event]}):
            result = await get_calendar_year_events(2026)
        assert "imsa" not in result
        assert "worldsbk" not in result
        assert result["formula1"] == [event]

    async def test_partial_provider_failure_does_not_crash(self) -> None:
        event = _weekend_event("formula2", start=datetime(2026, 3, 1, 13, 0, tzinfo=UTC))
        with (
            patch_weekend_sources({"formula2": [event]}),
            patch(
                _WEEKEND_SOURCE_PATHS["formula1"],
                AsyncMock(side_effect=httpx.TimeoutException("timeout")),
            ),
        ):
            result = await get_calendar_year_events(2026)
        assert "formula1" not in result
        assert result["formula2"] == [event]

    async def test_covers_every_registered_championship_not_only_weekend_subset(self) -> None:
        from motorsport_calendar.core.registry import registry

        registry.discover()
        with patch_weekend_sources():
            await get_calendar_year_events(2026)  # must not raise for any registered cid
        assert len(registry.list_all()) >= len(_WEEKEND_SOURCE_PATHS)

    async def test_refresh_flag_forwarded_to_source_factory(self) -> None:
        """MC-002 (P0-7) — "Mon calendrier"'s manual-refresh button calls
        this with refresh=True; every source it constructs must bypass the
        HTTP cache, not just the first one."""
        from motorsport_calendar.core.source_registry import source_registry

        real_get = source_registry.get
        captured_refresh: list[bool] = []

        def _spy_get(cid: str, source_name: str):
            real_factory = real_get(cid, source_name)

            def _wrapped(cache: object, refresh: bool):
                captured_refresh.append(refresh)
                return real_factory(cache, refresh)

            return _wrapped

        with (
            patch_weekend_sources(),
            patch.object(source_registry, "get", side_effect=_spy_get),
        ):
            await get_calendar_year_events(2026, refresh=True)

        assert captured_refresh
        assert all(captured_refresh)

    async def test_refresh_defaults_to_false(self) -> None:
        with patch_weekend_sources():
            result = await get_calendar_year_events(2026)  # must not raise without refresh=
        assert "formula1" in result

    async def test_championship_with_no_registered_source_is_skipped(self) -> None:
        from motorsport_calendar.core.source_registry import source_registry

        with (
            patch_weekend_sources(),
            patch.object(source_registry, "list_for", return_value=[]),
        ):
            result = await get_calendar_year_events(2026)
        assert result == {}

    async def test_championship_with_unregistered_provider_is_skipped(self) -> None:
        from motorsport_calendar.core.registry import registry

        with patch_weekend_sources(), patch.object(registry, "get", side_effect=KeyError("x")):
            result = await get_calendar_year_events(2026)
        assert result == {}


# ---------------------------------------------------------------------------
# TestCheckForUpdate (Sprint 51)
# ---------------------------------------------------------------------------


class TestCheckForUpdate:
    async def test_no_manifest_url_returns_no_update_without_network(self) -> None:
        """``manifest_url=""`` (empty override, mirrors the config.yaml
        default) must short-circuit before ever constructing an
        UpdateService/httpx client."""
        result = await check_for_update(current_version="0.4.9", manifest_url="")
        assert result.update_available is False
        assert result.current_version == "0.4.9"

    async def test_disabled_preference_short_circuits_before_url_resolution(self) -> None:
        """Even a real-looking manifest_url must never be fetched once the
        ``update_check_enabled`` preference is off — proven by passing a
        URL that would fail loudly if ``UpdateService`` ever tried it."""
        from motorsport_calendar.gui.preferences import load_preferences, save_preferences

        prefs = load_preferences()
        prefs["update_check_enabled"] = False
        save_preferences(prefs)

        from motorsport_calendar.gui.update_service import UpdateService

        with patch.object(
            UpdateService, "check_for_update", AsyncMock(side_effect=AssertionError("called"))
        ):
            result = await check_for_update(
                current_version="0.4.9",
                manifest_url="https://example.test/manifest.json",
            )
        assert result.update_available is False
        assert result.current_version == "0.4.9"

    async def test_enabled_preference_delegates_to_update_service(self) -> None:
        from motorsport_calendar.gui.update_service import (
            UpdateCheckResult,
            UpdateManifest,
            UpdateService,
        )

        expected = UpdateCheckResult(
            update_available=True,
            current_version="0.4.9",
            manifest=UpdateManifest(
                version="0.5.0",
                release_date="2026-07-12",
                title="Motorsport Calendar 0.5.0",
                summary="…",
                url="https://example.test/releases/0.5.0",
            ),
        )
        with patch.object(UpdateService, "check_for_update", AsyncMock(return_value=expected)):
            result = await check_for_update(
                current_version="0.4.9",
                manifest_url="https://example.test/manifest.json",
            )
        assert result == expected

    async def test_current_version_defaults_to_package_version(self) -> None:
        from motorsport_calendar import __version__

        result = await check_for_update(manifest_url="")
        assert result.current_version == __version__

    async def test_manifest_url_defaults_to_config_service(self) -> None:
        """No override passed — resolves from ``ConfigService().update.
        manifest_url``, empty by default (no config.yaml in the test
        environment), so this must not perform any network call."""
        result = await check_for_update(current_version="0.4.9")
        assert result.update_available is False


# ---------------------------------------------------------------------------
# TestPrepareNotifications (Sprint 56)
# ---------------------------------------------------------------------------


def _event_with_race(*, championship_id: str = "formula1", start: datetime) -> Event:
    championship = Championship(
        id=championship_id, name=championship_id, category=ChampionshipCategory.SINGLE_SEATER
    )
    circuit = Circuit(
        id="spa-circuit", name="Spa-Francorchamps", city="Spa", country="Belgium", timezone="UTC"
    )
    session = Session(
        type=SessionType.RACE,
        start_datetime=start,
        end_datetime=start + timedelta(hours=2),
        title="Race",
    )
    return Event(
        championship=championship,
        season=2026,
        round=1,
        name="Belgian",
        circuit=circuit,
        sessions=(session,),
        event_uid=f"{championship_id}-belgian@test",
    )


class TestPrepareNotifications:
    """ "Au démarrage, si les notifications sont activées, préparer les
    prochaines notifications" (Sprint 56 brief, verbatim). Covers every
    validation scenario the brief names explicitly: notifications
    disponibles/indisponibles, préférences désactivées, moteur vide,
    absence de plateforme compatible."""

    def test_disabled_preference_short_circuits_before_computing_anything(self) -> None:
        """ "préférences désactivées" — even a real upcoming session must
        never be computed once ``notifications_enabled`` is off, proven
        by patching ``compute_notifications`` to fail loudly if reached."""
        from motorsport_calendar.gui.notification_service import NotificationService
        from motorsport_calendar.gui.preferences import load_preferences, save_preferences

        prefs = load_preferences()
        prefs["notifications_enabled"] = False
        save_preferences(prefs)

        now = datetime(2026, 7, 12, 0, 0, tzinfo=UTC)
        year_events = {
            "formula1": [_event_with_race(start=now + timedelta(hours=2))],
        }
        with patch.object(
            NotificationService,
            "compute_notifications",
            side_effect=AssertionError("must never be called when disabled"),
        ):
            result = prepare_notifications(year_events, now=now)
        assert result == 0

    def test_empty_year_events_returns_zero(self) -> None:
        """ "moteur vide" — enabled, but nothing to compute from."""
        from motorsport_calendar.gui.preferences import load_preferences, save_preferences

        prefs = load_preferences()
        prefs["notifications_enabled"] = True
        save_preferences(prefs)

        assert prepare_notifications({}, now=datetime(2026, 7, 12, tzinfo=UTC)) == 0

    def test_enabled_with_upcoming_session_still_returns_zero_no_platform(self) -> None:
        """ "notifications indisponibles" / "absence de plateforme
        compatible" — real end-to-end path (enabled, real upcoming
        session computed), but the default system notifier
        (``NullSystemNotifier``) is always unavailable today, so nothing
        is ever actually shown — proven, not assumed."""
        from motorsport_calendar.gui.preferences import load_preferences, save_preferences

        prefs = load_preferences()
        prefs["notifications_enabled"] = True
        save_preferences(prefs)

        now = datetime(2026, 7, 12, 0, 0, tzinfo=UTC)
        year_events = {
            "formula1": [_event_with_race(start=now + timedelta(hours=2))],
        }
        assert prepare_notifications(year_events, now=now) == 0

    def test_enabled_delegates_to_notify_all_with_computed_notifications(self) -> None:
        """ "notifications disponibles" — proven by patching ``notify_all``
        with a stub that reports success, isolating this test from the
        real (always-unavailable) system notifier."""
        from motorsport_calendar.gui.preferences import load_preferences, save_preferences

        prefs = load_preferences()
        prefs["notifications_enabled"] = True
        save_preferences(prefs)

        now = datetime(2026, 7, 12, 0, 0, tzinfo=UTC)
        year_events = {
            "formula1": [_event_with_race(start=now + timedelta(hours=2))],
        }
        with patch(
            "motorsport_calendar.gui.system_notifications.notify_all", return_value=1
        ) as mock_notify_all:
            result = prepare_notifications(year_events, now=now)
        assert result == 1
        assert mock_notify_all.call_count == 1
        (dispatched,), _kwargs = mock_notify_all.call_args
        # A single RACE session (also the event's only/earliest one) anchors
        # 3 of the 5 kinds by default: WEEKEND_START, FIRST_SESSION, RACE —
        # QUALIFYING/SPRINT have no matching session, so none are produced.
        assert len(dispatched) == 3
        assert dispatched[0].championship_id == "formula1"

    def test_favorite_ids_forwarded_to_the_engine(self) -> None:
        from motorsport_calendar.gui.preferences import load_preferences, save_preferences

        prefs = load_preferences()
        prefs["notifications_enabled"] = True
        prefs["notifications_favorites_only"] = True
        save_preferences(prefs)

        now = datetime(2026, 7, 12, 0, 0, tzinfo=UTC)
        soon = now + timedelta(hours=2)
        year_events = {
            "formula1": [_event_with_race(championship_id="formula1", start=soon)],
            "motogp": [_event_with_race(championship_id="motogp", start=soon)],
        }
        with patch(
            "motorsport_calendar.gui.system_notifications.notify_all", return_value=0
        ) as mock_notify_all:
            prepare_notifications(year_events, now=now, favorite_ids=frozenset({"formula1"}))
        (dispatched,), _kwargs = mock_notify_all.call_args
        assert {n.championship_id for n in dispatched} == {"formula1"}

    def test_now_defaults_to_current_time_when_omitted(self) -> None:
        """A session far in the past never produces a notification when
        *now* is left to default to the real wall clock."""
        from motorsport_calendar.gui.preferences import load_preferences, save_preferences

        prefs = load_preferences()
        prefs["notifications_enabled"] = True
        save_preferences(prefs)

        year_events = {
            "formula1": [_event_with_race(start=datetime(2020, 1, 1, tzinfo=UTC))],
        }
        assert prepare_notifications(year_events) == 0
