"""Tests for GtwcEuropeProvider."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from motorsport_calendar.models import ChampionshipCategory, Event
from motorsport_calendar.providers.gtwc_europe.provider import GtwcEuropeProvider
from motorsport_calendar.providers.gtwc_europe.source import GtwcEuropeSource


def _make_source(events: list[Event] | None = None) -> GtwcEuropeSource:
    source = MagicMock(spec=GtwcEuropeSource)
    source.get_season = AsyncMock(return_value=events or [])
    return source


def _make_event(name: str = "Misano", season: int = 2026) -> MagicMock:
    e: Any = MagicMock(spec=Event)
    e.name = name
    e.season = season
    return e


class TestProviderIdentity:
    def test_name_is_gtwc_europe(self) -> None:
        provider = GtwcEuropeProvider(_make_source())
        assert provider.name == "gtwc-europe"

    def test_supported_championships_contains_gtwc_europe(self) -> None:
        provider = GtwcEuropeProvider(_make_source())
        assert "gtwc-europe" in provider.supported_championships

    def test_supported_championships_returns_list(self) -> None:
        provider = GtwcEuropeProvider(_make_source())
        assert isinstance(provider.supported_championships, list)


class TestFetchChampionship:
    async def test_returns_championship_object(self) -> None:
        provider = GtwcEuropeProvider(_make_source())
        champ = await provider.fetch_championship("gtwc-europe", 2026)
        assert champ is not None

    async def test_championship_name(self) -> None:
        provider = GtwcEuropeProvider(_make_source())
        champ = await provider.fetch_championship("gtwc-europe", 2026)
        assert champ.name == "GT World Challenge Europe Powered by AWS"

    async def test_championship_id_contains_year(self) -> None:
        provider = GtwcEuropeProvider(_make_source())
        champ = await provider.fetch_championship("gtwc-europe", 2026)
        assert "2026" in champ.id

    async def test_championship_id_contains_gtwc_europe(self) -> None:
        provider = GtwcEuropeProvider(_make_source())
        champ = await provider.fetch_championship("gtwc-europe", 2026)
        assert "gtwc-europe" in champ.id

    async def test_championship_category_gt(self) -> None:
        provider = GtwcEuropeProvider(_make_source())
        champ = await provider.fetch_championship("gtwc-europe", 2026)
        assert champ.category == ChampionshipCategory.GT


class TestFetchEvents:
    async def test_delegates_to_source_get_season(self) -> None:
        source = _make_source()
        provider = GtwcEuropeProvider(source)
        await provider.fetch_events("gtwc-europe", 2026)
        source.get_season.assert_awaited_once_with(2026)

    async def test_returns_events_from_source(self) -> None:
        events = [_make_event("Misano"), _make_event("Zandvoort")]
        provider = GtwcEuropeProvider(_make_source(events))
        result = await provider.fetch_events("gtwc-europe", 2026)
        assert len(result) == 2

    async def test_empty_source_returns_empty_list(self) -> None:
        provider = GtwcEuropeProvider(_make_source([]))
        result = await provider.fetch_events("gtwc-europe", 2026)
        assert result == []

    async def test_year_passed_to_source(self) -> None:
        source = _make_source()
        provider = GtwcEuropeProvider(source)
        await provider.fetch_events("gtwc-europe", 2027)
        source.get_season.assert_awaited_once_with(2027)

    async def test_source_exception_propagates(self) -> None:
        source = MagicMock(spec=GtwcEuropeSource)
        source.get_season = AsyncMock(side_effect=RuntimeError("network error"))
        provider = GtwcEuropeProvider(source)
        with pytest.raises(RuntimeError):
            await provider.fetch_events("gtwc-europe", 2026)
