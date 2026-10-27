"""Tests for FormulaEProvider."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from motorsport_calendar.models import ChampionshipCategory, Event
from motorsport_calendar.providers.formula_e.provider import FormulaEProvider
from motorsport_calendar.providers.formula_e.source import FormulaESource


def _make_source(events: list[Event] | None = None) -> FormulaESource:
    source = MagicMock(spec=FormulaESource)
    source.get_season = AsyncMock(return_value=events or [])
    return source


def _make_event(name: str = "Sao Paulo ePrix", season: int = 2025) -> MagicMock:
    e: Any = MagicMock(spec=Event)
    e.name = name
    e.season = season
    return e


class TestProviderIdentity:
    def test_name_is_formula_e(self) -> None:
        provider = FormulaEProvider(_make_source())
        assert provider.name == "formula-e"

    def test_supported_championships_contains_formula_e(self) -> None:
        provider = FormulaEProvider(_make_source())
        assert "formula-e" in provider.supported_championships

    def test_supported_championships_returns_list(self) -> None:
        provider = FormulaEProvider(_make_source())
        assert isinstance(provider.supported_championships, list)


class TestFetchChampionship:
    async def test_returns_championship_object(self) -> None:
        provider = FormulaEProvider(_make_source())
        champ = await provider.fetch_championship("formula-e", 2025)
        assert champ is not None

    async def test_championship_name_is_formula_e(self) -> None:
        provider = FormulaEProvider(_make_source())
        champ = await provider.fetch_championship("formula-e", 2025)
        assert champ.name == "Formula E"

    async def test_championship_id_contains_year(self) -> None:
        provider = FormulaEProvider(_make_source())
        champ = await provider.fetch_championship("formula-e", 2025)
        assert "2025" in champ.id

    async def test_championship_id_contains_formula_e(self) -> None:
        provider = FormulaEProvider(_make_source())
        champ = await provider.fetch_championship("formula-e", 2025)
        assert "formula-e" in champ.id

    async def test_championship_category_single_seater(self) -> None:
        provider = FormulaEProvider(_make_source())
        champ = await provider.fetch_championship("formula-e", 2025)
        assert champ.category == ChampionshipCategory.SINGLE_SEATER


class TestFetchEvents:
    async def test_delegates_to_source_get_season(self) -> None:
        source = _make_source()
        provider = FormulaEProvider(source)
        await provider.fetch_events("formula-e", 2025)
        source.get_season.assert_awaited_once_with(2025)

    async def test_returns_events_from_source(self) -> None:
        events = [_make_event("Sao Paulo ePrix"), _make_event("Mexico City ePrix")]
        provider = FormulaEProvider(_make_source(events))
        result = await provider.fetch_events("formula-e", 2025)
        assert len(result) == 2

    async def test_empty_source_returns_empty_list(self) -> None:
        provider = FormulaEProvider(_make_source([]))
        result = await provider.fetch_events("formula-e", 2025)
        assert result == []

    async def test_year_passed_to_source(self) -> None:
        source = _make_source()
        provider = FormulaEProvider(source)
        await provider.fetch_events("formula-e", 2026)
        source.get_season.assert_awaited_once_with(2026)

    async def test_source_exception_propagates(self) -> None:
        source = MagicMock(spec=FormulaESource)
        source.get_season = AsyncMock(side_effect=RuntimeError("network error"))
        provider = FormulaEProvider(source)
        with pytest.raises(RuntimeError):
            await provider.fetch_events("formula-e", 2025)
