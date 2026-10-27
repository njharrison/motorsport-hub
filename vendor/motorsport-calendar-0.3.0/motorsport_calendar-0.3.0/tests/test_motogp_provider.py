"""Tests for MotoGpProvider."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from motorsport_calendar.models import ChampionshipCategory, Event
from motorsport_calendar.providers.motogp.provider import MotoGpProvider
from motorsport_calendar.providers.motogp.source import MotoGpSource


def _make_source(events: list[Event] | None = None) -> MotoGpSource:
    source = MagicMock(spec=MotoGpSource)
    source.get_season = AsyncMock(return_value=events or [])
    return source


def _make_event(name: str = "Grand Prix of Thailand", season: int = 2026) -> MagicMock:
    e: Any = MagicMock(spec=Event)
    e.name = name
    e.season = season
    return e


class TestProviderIdentity:
    def test_name_is_motogp(self) -> None:
        provider = MotoGpProvider(_make_source())
        assert provider.name == "motogp"

    def test_supported_championships_contains_motogp(self) -> None:
        provider = MotoGpProvider(_make_source())
        assert "motogp" in provider.supported_championships

    def test_supported_championships_returns_list(self) -> None:
        provider = MotoGpProvider(_make_source())
        assert isinstance(provider.supported_championships, list)


class TestFetchChampionship:
    async def test_returns_championship_object(self) -> None:
        provider = MotoGpProvider(_make_source())
        champ = await provider.fetch_championship("motogp", 2026)
        assert champ is not None

    async def test_championship_name(self) -> None:
        provider = MotoGpProvider(_make_source())
        champ = await provider.fetch_championship("motogp", 2026)
        assert champ.name == "MotoGP"

    async def test_championship_id_contains_year(self) -> None:
        provider = MotoGpProvider(_make_source())
        champ = await provider.fetch_championship("motogp", 2026)
        assert "2026" in champ.id

    async def test_championship_id_contains_motogp(self) -> None:
        provider = MotoGpProvider(_make_source())
        champ = await provider.fetch_championship("motogp", 2026)
        assert "motogp" in champ.id

    async def test_championship_category_motorbike(self) -> None:
        provider = MotoGpProvider(_make_source())
        champ = await provider.fetch_championship("motogp", 2026)
        assert champ.category == ChampionshipCategory.MOTORBIKE


class TestFetchEvents:
    async def test_delegates_to_source_get_season(self) -> None:
        source = _make_source()
        provider = MotoGpProvider(source)
        await provider.fetch_events("motogp", 2026)
        source.get_season.assert_awaited_once_with(2026)

    async def test_returns_events_from_source(self) -> None:
        events = [_make_event("Grand Prix of Thailand"), _make_event("Grand Prix of Spain")]
        provider = MotoGpProvider(_make_source(events))
        result = await provider.fetch_events("motogp", 2026)
        assert len(result) == 2

    async def test_empty_source_returns_empty_list(self) -> None:
        provider = MotoGpProvider(_make_source([]))
        result = await provider.fetch_events("motogp", 2026)
        assert result == []

    async def test_year_passed_to_source(self) -> None:
        source = _make_source()
        provider = MotoGpProvider(source)
        await provider.fetch_events("motogp", 2027)
        source.get_season.assert_awaited_once_with(2027)

    async def test_source_exception_propagates(self) -> None:
        source = MagicMock(spec=MotoGpSource)
        source.get_season = AsyncMock(side_effect=RuntimeError("network error"))
        provider = MotoGpProvider(source)
        with pytest.raises(RuntimeError):
            await provider.fetch_events("motogp", 2026)
