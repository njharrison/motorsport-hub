"""Tests pour ProviderRegistry et les factories F1/WEC.

Structure :
- TestProviderRegistryUnit  : instances isolées, pas de singleton global
- TestProviderRegistryIntegration : singleton global + vraies factories

Note Sprint 10 : les factories de providers prennent maintenant (source) → Provider.
La sélection de la source appartient au SourceRegistry (tests dans test_source_registry.py).
"""

from __future__ import annotations

import pytest

from motorsport_calendar.config.models import ProviderConfig, ProvidersConfig
from motorsport_calendar.core.registry import ProviderRegistry, registry

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _dummy_factory(source):
    """Factory bidon pour les tests unitaires — prend une source, ne crée rien."""
    return object()


# ---------------------------------------------------------------------------
# Tests unitaires — ProviderRegistry isolé
# ---------------------------------------------------------------------------


class TestProviderRegistryUnit:
    """Tests avec une instance ProviderRegistry fraîche — aucun état global."""

    def test_register_and_get_returns_same_factory(self) -> None:
        reg = ProviderRegistry()
        reg.register("formula1", _dummy_factory)
        assert reg.get("formula1") is _dummy_factory

    def test_get_unknown_championship_raises_key_error(self) -> None:
        reg = ProviderRegistry()
        with pytest.raises(KeyError):
            reg.get("unknown")

    def test_get_error_message_contains_championship_id(self) -> None:
        reg = ProviderRegistry()
        with pytest.raises(KeyError, match="nonexistent"):
            reg.get("nonexistent")

    def test_get_error_message_lists_available_providers(self) -> None:
        reg = ProviderRegistry()
        reg.register("wec", _dummy_factory)
        with pytest.raises(KeyError, match="wec"):
            reg.get("f1")

    def test_list_all_empty_when_nothing_registered(self) -> None:
        reg = ProviderRegistry()
        assert reg.list_all() == []

    def test_list_all_returns_sorted_ids(self) -> None:
        reg = ProviderRegistry()
        reg.register("wec", _dummy_factory)
        reg.register("formula1", _dummy_factory)
        reg.register("f2", _dummy_factory)
        assert reg.list_all() == ["f2", "formula1", "wec"]

    def test_list_all_single_entry(self) -> None:
        reg = ProviderRegistry()
        reg.register("motogp", _dummy_factory)
        assert reg.list_all() == ["motogp"]

    def test_register_overwrites_existing_entry(self) -> None:
        reg = ProviderRegistry()

        def original(source):
            return None

        def replacement(source):
            return None

        reg.register("formula1", original)
        reg.register("formula1", replacement)
        assert reg.get("formula1") is replacement

    def test_enabled_includes_all_when_all_enabled_in_config(self) -> None:
        reg = ProviderRegistry()
        reg.register("formula1", _dummy_factory)
        reg.register("wec", _dummy_factory)
        cfg = ProvidersConfig()  # formula1 et wec activés par défaut
        result = reg.enabled(cfg)
        assert "formula1" in result
        assert "wec" in result

    def test_enabled_excludes_provider_with_enabled_false(self) -> None:
        reg = ProviderRegistry()
        reg.register("formula1", _dummy_factory)
        reg.register("wec", _dummy_factory)
        # wec désactivé explicitement
        cfg = ProvidersConfig(wec=ProviderConfig(source="official", enabled=False))
        result = reg.enabled(cfg)
        assert "formula1" in result
        assert "wec" not in result

    def test_enabled_includes_provider_absent_from_config(self) -> None:
        """Un provider non mentionné dans le YAML est activé par défaut (opt-out)."""
        reg = ProviderRegistry()
        reg.register("f3", _dummy_factory)  # f3 absent de ProvidersConfig
        cfg = ProvidersConfig()
        result = reg.enabled(cfg)
        assert "f3" in result

    def test_enabled_empty_registry_returns_empty_list(self) -> None:
        reg = ProviderRegistry()
        cfg = ProvidersConfig()
        assert reg.enabled(cfg) == []

    def test_enabled_all_disabled_returns_empty(self) -> None:
        reg = ProviderRegistry()
        reg.register("formula1", _dummy_factory)
        reg.register("wec", _dummy_factory)
        cfg = ProvidersConfig(
            formula1=ProviderConfig(source="openf1", enabled=False),
            wec=ProviderConfig(source="official", enabled=False),
        )
        assert reg.enabled(cfg) == []

    def test_enabled_result_is_sorted(self) -> None:
        reg = ProviderRegistry()
        reg.register("wec", _dummy_factory)
        reg.register("formula1", _dummy_factory)
        cfg = ProvidersConfig()
        result = reg.enabled(cfg)
        assert result == sorted(result)


# ---------------------------------------------------------------------------
# Tests d'intégration — singleton global + vraies factories
# ---------------------------------------------------------------------------


class TestProviderRegistryIntegration:
    """Tests avec le singleton global et les providers réels.

    Appelle registry.discover() pour garantir l'import des __init__.py.
    """

    def test_discover_registers_formula1(self) -> None:
        registry.discover()
        assert "formula1" in registry.list_all()

    def test_discover_registers_wec(self) -> None:
        registry.discover()
        assert "wec" in registry.list_all()

    def test_discover_is_idempotent(self) -> None:
        registry.discover()
        count_before = len(registry.list_all())
        registry.discover()
        assert len(registry.list_all()) == count_before

    def test_formula1_factory_wraps_source_in_formula1_provider(self) -> None:
        """La factory F1 prend une source et retourne un Formula1Provider."""
        from motorsport_calendar.providers.formula1 import Formula1Provider
        from motorsport_calendar.providers.formula1.sources.openf1 import OpenF1Source

        registry.discover()
        factory = registry.get("formula1")
        source = OpenF1Source()
        provider = factory(source)
        assert isinstance(provider, Formula1Provider)
        assert provider._source is source

    def test_wec_factory_wraps_source_in_wec_provider(self) -> None:
        """La factory WEC prend une source et retourne un WecProvider."""
        from motorsport_calendar.providers.wec import WecProvider
        from motorsport_calendar.providers.wec.sources.official import OfficialWecSource

        registry.discover()
        factory = registry.get("wec")
        source = OfficialWecSource()
        provider = factory(source)
        assert isinstance(provider, WecProvider)
        assert provider._source is source

    def test_enabled_returns_formula1_and_wec_with_default_config(self) -> None:
        registry.discover()
        cfg = ProvidersConfig()
        enabled = registry.enabled(cfg)
        assert "formula1" in enabled
        assert "wec" in enabled

    def test_enabled_excludes_disabled_provider_from_yaml(self) -> None:
        """Simulation d'un YAML avec wec: { enabled: false }."""
        registry.discover()
        cfg = ProvidersConfig.model_validate({"wec": {"source": "official", "enabled": False}})
        enabled = registry.enabled(cfg)
        assert "formula1" in enabled
        assert "wec" not in enabled
