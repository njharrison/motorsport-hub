"""Tests for Formula3Provider."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from motorsport_calendar.models import ChampionshipCategory, Event
from motorsport_calendar.providers.formula3.provider import Formula3Provider
from motorsport_calendar.providers.formula3.source import Formula3Source


def _make_source(events: list[Event] | None = None) -> Formula3Source:
    source = MagicMock(spec=Formula3Source)
    source.get_season = AsyncMock(return_value=events or [])
    return source


def _make_event(name: str = "Bahrain GP", season: int = 2025) -> MagicMock:
    e: Any = MagicMock(spec=Event)
    e.name = name
    e.season = season
    return e


class TestProviderIdentity:
    def test_name_is_formula3(self) -> None:
        provider = Formula3Provider(_make_source())
        assert provider.name == "formula3"

    def test_supported_championships_contains_formula3(self) -> None:
        provider = Formula3Provider(_make_source())
        assert "formula3" in provider.supported_championships

    def test_supported_championships_returns_list(self) -> None:
        provider = Formula3Provider(_make_source())
        assert isinstance(provider.supported_championships, list)


class TestFetchChampionship:
    async def test_returns_championship_object(self) -> None:
        provider = Formula3Provider(_make_source())
        champ = await provider.fetch_championship("formula3", 2025)
        assert champ is not None

    async def test_championship_name_contains_formula_3(self) -> None:
        provider = Formula3Provider(_make_source())
        champ = await provider.fetch_championship("formula3", 2025)
        assert "Formula 3" in champ.name

    async def test_championship_id_contains_year(self) -> None:
        provider = Formula3Provider(_make_source())
        champ = await provider.fetch_championship("formula3", 2025)
        assert "2025" in champ.id

    async def test_championship_category_single_seater(self) -> None:
        provider = Formula3Provider(_make_source())
        champ = await provider.fetch_championship("formula3", 2025)
        assert champ.category == ChampionshipCategory.SINGLE_SEATER


class TestFetchEvents:
    async def test_delegates_to_source_get_season(self) -> None:
        source = _make_source()
        provider = Formula3Provider(source)
        await provider.fetch_events("formula3", 2025)
        source.get_season.assert_awaited_once_with(2025)

    async def test_returns_events_from_source(self) -> None:
        events = [_make_event("Bahrain GP"), _make_event("Monaco GP")]
        provider = Formula3Provider(_make_source(events))
        result = await provider.fetch_events("formula3", 2025)
        assert len(result) == 2

    async def test_empty_source_returns_empty_list(self) -> None:
        provider = Formula3Provider(_make_source([]))
        result = await provider.fetch_events("formula3", 2025)
        assert result == []

    async def test_year_passed_to_source(self) -> None:
        source = _make_source()
        provider = Formula3Provider(source)
        await provider.fetch_events("formula3", 2026)
        source.get_season.assert_awaited_once_with(2026)

    async def test_source_exception_propagates(self) -> None:
        source = MagicMock(spec=Formula3Source)
        source.get_season = AsyncMock(side_effect=RuntimeError("network error"))
        provider = Formula3Provider(source)
        with pytest.raises(RuntimeError):
            await provider.fetch_events("formula3", 2025)
