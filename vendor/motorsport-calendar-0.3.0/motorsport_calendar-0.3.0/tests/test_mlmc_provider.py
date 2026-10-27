"""Tests for MlmcProvider."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from motorsport_calendar.models import ChampionshipCategory, Event
from motorsport_calendar.providers.mlmc.provider import MlmcProvider
from motorsport_calendar.providers.mlmc.source import MlmcSource


def _make_source(events: list[Event] | None = None) -> MlmcSource:
    source = MagicMock(spec=MlmcSource)
    source.get_season = AsyncMock(return_value=events or [])
    return source


def _make_event(name: str = "Barcelona Round", season: int = 2026) -> MagicMock:
    e: Any = MagicMock(spec=Event)
    e.name = name
    e.season = season
    return e


class TestProviderIdentity:
    def test_name_is_mlmc(self) -> None:
        provider = MlmcProvider(_make_source())
        assert provider.name == "mlmc"

    def test_supported_championships_contains_mlmc(self) -> None:
        provider = MlmcProvider(_make_source())
        assert "mlmc" in provider.supported_championships

    def test_supported_championships_returns_list(self) -> None:
        provider = MlmcProvider(_make_source())
        assert isinstance(provider.supported_championships, list)


class TestFetchChampionship:
    async def test_returns_championship_object(self) -> None:
        provider = MlmcProvider(_make_source())
        champ = await provider.fetch_championship("mlmc", 2026)
        assert champ is not None

    async def test_championship_name(self) -> None:
        provider = MlmcProvider(_make_source())
        champ = await provider.fetch_championship("mlmc", 2026)
        assert champ.name == "Michelin Le Mans Cup"

    async def test_championship_id_contains_year(self) -> None:
        provider = MlmcProvider(_make_source())
        champ = await provider.fetch_championship("mlmc", 2026)
        assert "2026" in champ.id

    async def test_championship_id_contains_mlmc(self) -> None:
        provider = MlmcProvider(_make_source())
        champ = await provider.fetch_championship("mlmc", 2026)
        assert "mlmc" in champ.id

    async def test_championship_category_endurance(self) -> None:
        provider = MlmcProvider(_make_source())
        champ = await provider.fetch_championship("mlmc", 2026)
        assert champ.category == ChampionshipCategory.ENDURANCE


class TestFetchEvents:
    async def test_delegates_to_source_get_season(self) -> None:
        source = _make_source()
        provider = MlmcProvider(source)
        await provider.fetch_events("mlmc", 2026)
        source.get_season.assert_awaited_once_with(2026)

    async def test_returns_events_from_source(self) -> None:
        events = [_make_event("Barcelona Round"), _make_event("Road To Le Mans")]
        provider = MlmcProvider(_make_source(events))
        result = await provider.fetch_events("mlmc", 2026)
        assert len(result) == 2

    async def test_road_to_le_mans_is_just_another_event_no_special_casing(self) -> None:
        """RTLM flows through the provider like any other round — no
        separate championship_id, matching how the site itself lists it
        as one more round on the MLMC season page (Sprint 35)."""
        events = [_make_event("Road To Le Mans")]
        provider = MlmcProvider(_make_source(events))
        result = await provider.fetch_events("mlmc", 2026)
        assert result[0].name == "Road To Le Mans"

    async def test_empty_source_returns_empty_list(self) -> None:
        provider = MlmcProvider(_make_source([]))
        result = await provider.fetch_events("mlmc", 2026)
        assert result == []

    async def test_year_passed_to_source(self) -> None:
        source = _make_source()
        provider = MlmcProvider(source)
        await provider.fetch_events("mlmc", 2027)
        source.get_season.assert_awaited_once_with(2027)

    async def test_source_exception_propagates(self) -> None:
        source = MagicMock(spec=MlmcSource)
        source.get_season = AsyncMock(side_effect=RuntimeError("network error"))
        provider = MlmcProvider(source)
        with pytest.raises(RuntimeError):
            await provider.fetch_events("mlmc", 2026)
