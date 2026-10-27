"""Tests pour SourceRegistry et les factories de sources F1/WEC.

Structure :
- TestSourceRegistryUnit        : instances isolées, pas de singleton global
- TestSourceRegistryIntegration : singleton global + vraies sources
"""

from __future__ import annotations

import pytest

from motorsport_calendar.core.source_registry import SourceRegistry, source_registry

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _dummy_factory(cache, refresh):
    """Factory bidon pour les tests unitaires."""
    return object()


# ---------------------------------------------------------------------------
# Tests unitaires — SourceRegistry isolé
# ---------------------------------------------------------------------------


class TestSourceRegistryUnit:
    """Tests avec une instance SourceRegistry fraîche — aucun état global."""

    def test_register_and_get_returns_same_factory(self) -> None:
        reg = SourceRegistry()
        reg.register("formula1", "openf1", _dummy_factory)
        assert reg.get("formula1", "openf1") is _dummy_factory

    def test_get_unknown_source_raises_key_error(self) -> None:
        reg = SourceRegistry()
        reg.register("formula1", "openf1", _dummy_factory)
        with pytest.raises(KeyError):
            reg.get("formula1", "ergast")

    def test_get_unknown_championship_raises_key_error(self) -> None:
        reg = SourceRegistry()
        with pytest.raises(KeyError):
            reg.get("motogp", "official")

    def test_get_error_message_contains_championship_id(self) -> None:
        reg = SourceRegistry()
        with pytest.raises(KeyError, match="formula1"):
            reg.get("formula1", "ergast")

    def test_get_error_message_contains_source_name(self) -> None:
        reg = SourceRegistry()
        with pytest.raises(KeyError, match="ergast"):
            reg.get("formula1", "ergast")

    def test_get_error_message_lists_available_sources(self) -> None:
        reg = SourceRegistry()
        reg.register("formula1", "openf1", _dummy_factory)
        with pytest.raises(KeyError, match="openf1"):
            reg.get("formula1", "ergast")

    def test_list_for_returns_sources_for_championship(self) -> None:
        reg = SourceRegistry()
        reg.register("formula1", "openf1", _dummy_factory)
        reg.register("formula1", "ergast", _dummy_factory)
        assert reg.list_for("formula1") == ["ergast", "openf1"]

    def test_list_for_returns_empty_for_unknown_championship(self) -> None:
        reg = SourceRegistry()
        assert reg.list_for("motogp") == []

    def test_list_for_excludes_other_championships(self) -> None:
        reg = SourceRegistry()
        reg.register("formula1", "openf1", _dummy_factory)
        reg.register("wec", "official", _dummy_factory)
        assert reg.list_for("formula1") == ["openf1"]
        assert reg.list_for("wec") == ["official"]

    def test_list_for_returns_sorted(self) -> None:
        reg = SourceRegistry()
        reg.register("formula1", "openf1", _dummy_factory)
        reg.register("formula1", "ergast", _dummy_factory)
        reg.register("formula1", "jolpica", _dummy_factory)
        result = reg.list_for("formula1")
        assert result == sorted(result)

    def test_list_all_returns_sorted_pairs(self) -> None:
        reg = SourceRegistry()
        reg.register("wec", "official", _dummy_factory)
        reg.register("formula1", "openf1", _dummy_factory)
        result = reg.list_all()
        assert result == sorted(result)
        assert ("formula1", "openf1") in result
        assert ("wec", "official") in result

    def test_list_all_empty_when_nothing_registered(self) -> None:
        reg = SourceRegistry()
        assert reg.list_all() == []

    def test_register_overwrites_existing_factory(self) -> None:
        reg = SourceRegistry()

        def original(cache, refresh):
            return None

        def replacement(cache, refresh):
            return None

        reg.register("formula1", "openf1", original)
        reg.register("formula1", "openf1", replacement)
        assert reg.get("formula1", "openf1") is replacement

    def test_different_championships_do_not_conflict(self) -> None:
        """formula1/openf1 et wec/openf1 sont des clés distinctes."""
        reg = SourceRegistry()

        def f1_factory(cache, refresh):
            return "f1-source"

        def wec_factory(cache, refresh):
            return "wec-source"

        reg.register("formula1", "openf1", f1_factory)
        reg.register("wec", "openf1", wec_factory)
        assert reg.get("formula1", "openf1") is f1_factory
        assert reg.get("wec", "openf1") is wec_factory


# ---------------------------------------------------------------------------
# Tests d'intégration — singleton global + vraies sources
# ---------------------------------------------------------------------------


class TestSourceRegistryIntegration:
    """Tests avec le singleton global source_registry.

    Appelle source_registry.discover() pour garantir l'import des sources/__init__.py.
    """

    def test_discover_registers_formula1_openf1(self) -> None:
        source_registry.discover()
        assert ("formula1", "openf1") in source_registry.list_all()

    def test_discover_registers_wec_official(self) -> None:
        source_registry.discover()
        assert ("wec", "official") in source_registry.list_all()

    def test_discover_is_idempotent(self) -> None:
        source_registry.discover()
        count_before = len(source_registry.list_all())
        source_registry.discover()
        assert len(source_registry.list_all()) == count_before

    def test_list_for_formula1_includes_openf1(self) -> None:
        source_registry.discover()
        assert "openf1" in source_registry.list_for("formula1")

    def test_list_for_wec_includes_official(self) -> None:
        source_registry.discover()
        assert "official" in source_registry.list_for("wec")

    def test_formula1_openf1_factory_creates_openf1_source(self) -> None:
        from motorsport_calendar.providers.formula1.sources.openf1 import OpenF1Source

        source_registry.discover()
        make_source = source_registry.get("formula1", "openf1")
        source = make_source(None, False)
        assert isinstance(source, OpenF1Source)

    def test_formula1_openf1_factory_with_none_cache(self) -> None:
        """cache=None est valide — le client httpx sera créé dans OpenF1Source."""
        source_registry.discover()
        make_source = source_registry.get("formula1", "openf1")
        source = make_source(None, False)
        assert source is not None

    def test_formula1_openf1_factory_passes_refresh_true(self) -> None:
        source_registry.discover()
        make_source = source_registry.get("formula1", "openf1")
        source = make_source(None, True)
        assert source._refresh is True

    def test_formula1_openf1_factory_passes_refresh_false(self) -> None:
        source_registry.discover()
        make_source = source_registry.get("formula1", "openf1")
        source = make_source(None, False)
        assert source._refresh is False

    def test_formula1_openf1_factory_passes_cache(self) -> None:
        from pathlib import Path

        from motorsport_calendar.cache import HttpCache

        source_registry.discover()
        make_source = source_registry.get("formula1", "openf1")
        cache = HttpCache(cache_dir=Path(".cache"), ttl=3600)
        source = make_source(cache, False)
        assert source._cache is cache

    def test_wec_official_factory_creates_official_wec_source(self) -> None:
        from motorsport_calendar.providers.wec.sources.official import OfficialWecSource

        source_registry.discover()
        make_source = source_registry.get("wec", "official")
        source = make_source(None, False)
        assert isinstance(source, OfficialWecSource)

    def test_unknown_source_for_known_championship_raises_key_error(self) -> None:
        source_registry.discover()
        with pytest.raises(KeyError, match="ergast"):
            source_registry.get("formula1", "ergast")

    def test_unknown_championship_raises_key_error(self) -> None:
        source_registry.discover()
        with pytest.raises(KeyError, match="motogp"):
            source_registry.get("motogp", "official")
