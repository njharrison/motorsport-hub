"""Tests for IgtcProvider."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from motorsport_calendar.models import ChampionshipCategory, Event
from motorsport_calendar.providers.igtc.provider import IgtcProvider
from motorsport_calendar.providers.igtc.source import IgtcSource


def _make_source(events: list[Event] | None = None) -> IgtcSource:
    source = MagicMock(spec=IgtcSource)
    source.get_season = AsyncMock(return_value=events or [])
    return source


def _make_event(name: str = "Bathurst 12 Hour", season: int = 2026) -> MagicMock:
    e: Any = MagicMock(spec=Event)
    e.name = name
    e.season = season
    return e


class TestProviderIdentity:
    def test_name_is_igtc(self) -> None:
        provider = IgtcProvider(_make_source())
        assert provider.name == "igtc"

    def test_supported_championships_contains_igtc(self) -> None:
        provider = IgtcProvider(_make_source())
        assert "igtc" in provider.supported_championships

    def test_supported_championships_returns_list(self) -> None:
        provider = IgtcProvider(_make_source())
        assert isinstance(provider.supported_championships, list)


class TestFetchChampionship:
    async def test_returns_championship_object(self) -> None:
        provider = IgtcProvider(_make_source())
        champ = await provider.fetch_championship("igtc", 2026)
        assert champ is not None

    async def test_championship_name(self) -> None:
        provider = IgtcProvider(_make_source())
        champ = await provider.fetch_championship("igtc", 2026)
        assert champ.name == "Intercontinental GT Challenge"

    async def test_championship_id_contains_year(self) -> None:
        provider = IgtcProvider(_make_source())
        champ = await provider.fetch_championship("igtc", 2026)
        assert "2026" in champ.id

    async def test_championship_id_contains_igtc(self) -> None:
        provider = IgtcProvider(_make_source())
        champ = await provider.fetch_championship("igtc", 2026)
        assert "igtc" in champ.id

    async def test_championship_category_gt(self) -> None:
        provider = IgtcProvider(_make_source())
        champ = await provider.fetch_championship("igtc", 2026)
        assert champ.category == ChampionshipCategory.GT


class TestFetchEvents:
    async def test_delegates_to_source_get_season(self) -> None:
        source = _make_source()
        provider = IgtcProvider(source)
        await provider.fetch_events("igtc", 2026)
        source.get_season.assert_awaited_once_with(2026)

    async def test_returns_events_from_source(self) -> None:
        events = [_make_event("Bathurst 12 Hour"), _make_event("24 Hours of Spa")]
        provider = IgtcProvider(_make_source(events))
        result = await provider.fetch_events("igtc", 2026)
        assert len(result) == 2

    async def test_empty_source_returns_empty_list(self) -> None:
        provider = IgtcProvider(_make_source([]))
        result = await provider.fetch_events("igtc", 2026)
        assert result == []

    async def test_year_passed_to_source(self) -> None:
        source = _make_source()
        provider = IgtcProvider(source)
        await provider.fetch_events("igtc", 2027)
        source.get_season.assert_awaited_once_with(2027)

    async def test_source_exception_propagates(self) -> None:
        source = MagicMock(spec=IgtcSource)
        source.get_season = AsyncMock(side_effect=RuntimeError("network error"))
        provider = IgtcProvider(source)
        with pytest.raises(RuntimeError):
            await provider.fetch_events("igtc", 2026)
