"""Tests for GtwcAmericaProvider."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from motorsport_calendar.models import ChampionshipCategory, Event
from motorsport_calendar.providers.gtwc_america.provider import GtwcAmericaProvider
from motorsport_calendar.providers.gtwc_america.source import GtwcAmericaSource


def _make_source(events: list[Event] | None = None) -> GtwcAmericaSource:
    source = MagicMock(spec=GtwcAmericaSource)
    source.get_season = AsyncMock(return_value=events or [])
    return source


def _make_event(name: str = "Circuit of the Americas", season: int = 2026) -> MagicMock:
    e: Any = MagicMock(spec=Event)
    e.name = name
    e.season = season
    return e


class TestProviderIdentity:
    def test_name_is_gtwc_america(self) -> None:
        provider = GtwcAmericaProvider(_make_source())
        assert provider.name == "gtwc-america"

    def test_supported_championships_contains_gtwc_america(self) -> None:
        provider = GtwcAmericaProvider(_make_source())
        assert "gtwc-america" in provider.supported_championships

    def test_supported_championships_returns_list(self) -> None:
        provider = GtwcAmericaProvider(_make_source())
        assert isinstance(provider.supported_championships, list)


class TestFetchChampionship:
    async def test_returns_championship_object(self) -> None:
        provider = GtwcAmericaProvider(_make_source())
        champ = await provider.fetch_championship("gtwc-america", 2026)
        assert champ is not None

    async def test_championship_name(self) -> None:
        provider = GtwcAmericaProvider(_make_source())
        champ = await provider.fetch_championship("gtwc-america", 2026)
        assert champ.name == "GT World Challenge America Powered by AWS"

    async def test_championship_id_contains_year(self) -> None:
        provider = GtwcAmericaProvider(_make_source())
        champ = await provider.fetch_championship("gtwc-america", 2026)
        assert "2026" in champ.id

    async def test_championship_id_contains_gtwc_america(self) -> None:
        provider = GtwcAmericaProvider(_make_source())
        champ = await provider.fetch_championship("gtwc-america", 2026)
        assert "gtwc-america" in champ.id

    async def test_championship_category_gt(self) -> None:
        provider = GtwcAmericaProvider(_make_source())
        champ = await provider.fetch_championship("gtwc-america", 2026)
        assert champ.category == ChampionshipCategory.GT


class TestFetchEvents:
    async def test_delegates_to_source_get_season(self) -> None:
        source = _make_source()
        provider = GtwcAmericaProvider(source)
        await provider.fetch_events("gtwc-america", 2026)
        source.get_season.assert_awaited_once_with(2026)

    async def test_returns_events_from_source(self) -> None:
        events = [_make_event("Sonoma Raceway"), _make_event("Road Atlanta")]
        provider = GtwcAmericaProvider(_make_source(events))
        result = await provider.fetch_events("gtwc-america", 2026)
        assert len(result) == 2

    async def test_empty_source_returns_empty_list(self) -> None:
        provider = GtwcAmericaProvider(_make_source([]))
        result = await provider.fetch_events("gtwc-america", 2026)
        assert result == []

    async def test_year_passed_to_source(self) -> None:
        source = _make_source()
        provider = GtwcAmericaProvider(source)
        await provider.fetch_events("gtwc-america", 2027)
        source.get_season.assert_awaited_once_with(2027)

    async def test_source_exception_propagates(self) -> None:
        source = MagicMock(spec=GtwcAmericaSource)
        source.get_season = AsyncMock(side_effect=RuntimeError("network error"))
        provider = GtwcAmericaProvider(source)
        with pytest.raises(RuntimeError):
            await provider.fetch_events("gtwc-america", 2026)
