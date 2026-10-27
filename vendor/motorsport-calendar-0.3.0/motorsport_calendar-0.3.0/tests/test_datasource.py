"""Tests for the Data Acquisition Layer — core/datasource/."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import httpx
import pytest

from motorsport_calendar.core.datasource import (
    DataSource,
    HtmlDataSource,
    IcsDataSource,
    JsonDataSource,
)
from motorsport_calendar.providers.formula1.sources.openf1 import OpenF1Source

# ---------------------------------------------------------------------------
# Minimal concrete implementations for instantiation tests
# ---------------------------------------------------------------------------


class _ConcreteJsonSource(JsonDataSource):
    async def fetch_json(self, url: str, params: dict[str, Any]) -> list | dict:
        return []


class _ConcreteHtmlSource(HtmlDataSource):
    async def fetch_html(self, url: str) -> str:
        return ""


class _ConcreteIcsSource(IcsDataSource):
    async def fetch_ics(self, url: str) -> str:
        return ""


class _IncompleteJsonSource(JsonDataSource):
    """Missing fetch_json — cannot be instantiated."""


class _IncompleteHtmlSource(HtmlDataSource):
    """Missing fetch_html — cannot be instantiated."""


class _IncompleteIcsSource(IcsDataSource):
    """Missing fetch_ics — cannot be instantiated."""


# ---------------------------------------------------------------------------
# DataSource base
# ---------------------------------------------------------------------------


class TestDataSourceBase:
    def test_is_importable_and_is_abstract(self) -> None:
        import abc

        assert issubclass(DataSource, abc.ABC)

    def test_json_html_ics_all_inherit_from_data_source(self) -> None:
        assert issubclass(JsonDataSource, DataSource)
        assert issubclass(HtmlDataSource, DataSource)
        assert issubclass(IcsDataSource, DataSource)


# ---------------------------------------------------------------------------
# JsonDataSource
# ---------------------------------------------------------------------------


class TestJsonDataSource:
    def test_cannot_instantiate_directly(self) -> None:
        with pytest.raises(TypeError):
            JsonDataSource()  # type: ignore[abstract]

    def test_subclass_without_fetch_json_cannot_instantiate(self) -> None:
        with pytest.raises(TypeError):
            _IncompleteJsonSource()  # type: ignore[abstract]

    def test_concrete_subclass_can_instantiate(self) -> None:
        source = _ConcreteJsonSource()
        assert isinstance(source, JsonDataSource)

    def test_concrete_subclass_is_data_source(self) -> None:
        assert isinstance(_ConcreteJsonSource(), DataSource)

    async def test_concrete_fetch_json_is_awaitable(self) -> None:
        source = _ConcreteJsonSource()
        result = await source.fetch_json("http://example.com", {})
        assert result == []


# ---------------------------------------------------------------------------
# HtmlDataSource
# ---------------------------------------------------------------------------


class TestHtmlDataSource:
    def test_cannot_instantiate_directly(self) -> None:
        with pytest.raises(TypeError):
            HtmlDataSource()  # type: ignore[abstract]

    def test_subclass_without_fetch_html_cannot_instantiate(self) -> None:
        with pytest.raises(TypeError):
            _IncompleteHtmlSource()  # type: ignore[abstract]

    def test_concrete_subclass_can_instantiate(self) -> None:
        source = _ConcreteHtmlSource()
        assert isinstance(source, HtmlDataSource)

    def test_concrete_subclass_is_data_source(self) -> None:
        assert isinstance(_ConcreteHtmlSource(), DataSource)

    async def test_concrete_fetch_html_is_awaitable(self) -> None:
        source = _ConcreteHtmlSource()
        result = await source.fetch_html("http://example.com")
        assert result == ""


# ---------------------------------------------------------------------------
# IcsDataSource
# ---------------------------------------------------------------------------


class TestIcsDataSource:
    def test_cannot_instantiate_directly(self) -> None:
        with pytest.raises(TypeError):
            IcsDataSource()  # type: ignore[abstract]

    def test_subclass_without_fetch_ics_cannot_instantiate(self) -> None:
        with pytest.raises(TypeError):
            _IncompleteIcsSource()  # type: ignore[abstract]

    def test_concrete_subclass_can_instantiate(self) -> None:
        source = _ConcreteIcsSource()
        assert isinstance(source, IcsDataSource)

    def test_concrete_subclass_is_data_source(self) -> None:
        assert isinstance(_ConcreteIcsSource(), DataSource)

    async def test_concrete_fetch_ics_is_awaitable(self) -> None:
        source = _ConcreteIcsSource()
        result = await source.fetch_ics("http://example.com/feed.ics")
        assert result == ""


# ---------------------------------------------------------------------------
# OpenF1Source migration validation
# ---------------------------------------------------------------------------


class TestOpenF1SourceMigration:
    def test_openf1_is_subclass_of_json_data_source(self) -> None:
        assert issubclass(OpenF1Source, JsonDataSource)

    def test_openf1_is_subclass_of_data_source(self) -> None:
        assert issubclass(OpenF1Source, DataSource)

    def test_openf1_instance_is_json_data_source(self) -> None:
        client = MagicMock(spec=httpx.AsyncClient)
        source = OpenF1Source(client=client)
        assert isinstance(source, JsonDataSource)

    def test_openf1_implements_fetch_json(self) -> None:
        import inspect

        assert not inspect.isabstract(OpenF1Source)

    async def test_fetch_json_returns_data_from_http(self) -> None:
        expected = [{"meeting_key": 1229, "meeting_name": "Bahrain Grand Prix"}]

        async def fake_get(path: str, *, params: dict | None = None) -> MagicMock:
            resp = MagicMock(spec=httpx.Response)
            resp.raise_for_status.return_value = None
            resp.json.return_value = expected
            return resp

        client = MagicMock(spec=httpx.AsyncClient)
        client.get = fake_get
        source = OpenF1Source(client=client)

        result = await source.fetch_json("https://api.openf1.org/v1/meetings", {"year": 2024})
        assert result == expected

    async def test_fetch_json_propagates_http_error(self) -> None:
        async def fake_get(path: str, *, params: dict | None = None) -> MagicMock:
            request = httpx.Request("GET", f"https://api.openf1.org/v1{path}")
            response = httpx.Response(503, request=request)
            raise httpx.HTTPStatusError("503", request=request, response=response)

        client = MagicMock(spec=httpx.AsyncClient)
        client.get = fake_get
        source = OpenF1Source(client=client)

        with pytest.raises(httpx.HTTPStatusError):
            await source.fetch_json("https://api.openf1.org/v1/meetings", {"year": 2024})

    async def test_fetch_json_propagates_timeout(self) -> None:
        async def fake_get(path: str, *, params: dict | None = None) -> MagicMock:
            raise httpx.TimeoutException("timeout")

        client = MagicMock(spec=httpx.AsyncClient)
        client.get = fake_get
        source = OpenF1Source(client=client)

        with pytest.raises(httpx.TimeoutException):
            await source.fetch_json("https://api.openf1.org/v1/sessions", {"year": 2024})

    async def test_get_season_still_works_after_migration(self) -> None:
        """Existing get_season API is unchanged — full pipeline must still work."""
        meetings = [
            {
                "meeting_key": 1229,
                "meeting_name": "Bahrain Grand Prix",
                "location": "Sakhir",
                "country_name": "Bahrain",
                "circuit_key": 1,
                "circuit_short_name": "Sakhir",
                "date_start": "2024-03-02T15:00:00+00:00",
                "year": 2024,
            }
        ]
        sessions: list[dict] = []

        async def fake_get(path: str, *, params: dict | None = None) -> MagicMock:
            resp = MagicMock(spec=httpx.Response)
            resp.raise_for_status.return_value = None
            resp.json.return_value = meetings if "meetings" in path else sessions
            return resp

        client = MagicMock(spec=httpx.AsyncClient)
        client.get = fake_get
        source = OpenF1Source(client=client)

        events = await source.get_season(2024)
        assert len(events) == 1
        assert events[0].name == "Bahrain Grand Prix"
