"""Tests pour les modèles de configuration et ConfigService."""

from __future__ import annotations

from pathlib import Path
import sys

from pydantic import ValidationError
import pytest

from motorsport_calendar.config import (
    AppConfig,
    CacheConfig,
    ConfigService,
    IcsConfig,
    ProviderConfig,
    ProvidersConfig,
    UpdateConfig,
)
from motorsport_calendar.utils.paths import user_cache_dir, user_config_dir

# ---------------------------------------------------------------------------
# Modèles — valeurs par défaut
# ---------------------------------------------------------------------------


class TestAppConfigDefaults:
    def test_default_timezone(self) -> None:
        assert AppConfig().timezone == "Europe/Paris"

    def test_default_cache_enabled(self) -> None:
        assert AppConfig().cache.enabled is True

    def test_default_cache_ttl_hours(self) -> None:
        assert AppConfig().cache.ttl_hours == 24

    def test_default_cache_path_contains_cache_dir(self) -> None:
        path = str(AppConfig().cache.path)
        assert "motorsport-calendar" in path
        if sys.platform != "win32":
            # Windows uses %LOCALAPPDATA%\motorsport-calendar, no ".cache"
            # segment — see utils/paths.py::user_cache_dir.
            assert ".cache" in path

    def test_default_cache_path_matches_user_cache_dir(self) -> None:
        """Sprint 49 — the default must be the platform user cache
        directory (utils/paths.py), never the current working directory."""
        assert AppConfig().cache.path == user_cache_dir("motorsport-calendar")

    def test_default_ics_alarm_minutes(self) -> None:
        assert AppConfig().ics.alarm_minutes == 30

    def test_default_f1_source_is_openf1(self) -> None:
        assert AppConfig().providers.formula1.source == "openf1"

    def test_default_wec_source_is_official(self) -> None:
        assert AppConfig().providers.wec.source == "official"

    def test_default_update_manifest_url_is_empty(self) -> None:
        """Sprint 51 — no host is ever hardcoded (no GitHub, no anything);
        an empty default means the update check is a silent no-op until a
        real URL is set in config.yaml."""
        assert AppConfig().update.manifest_url == ""


class TestCacheConfigProperties:
    def test_ttl_seconds_converts_hours(self) -> None:
        cache = CacheConfig(ttl_hours=24)
        assert cache.ttl_seconds == 86400

    def test_ttl_seconds_custom(self) -> None:
        cache = CacheConfig(ttl_hours=1)
        assert cache.ttl_seconds == 3600

    def test_resolved_path_expands_tilde(self) -> None:
        cache = CacheConfig(path=Path("~/.cache/test"))
        resolved = cache.resolved_path
        assert "~" not in str(resolved)
        assert resolved.is_absolute()

    def test_resolved_path_absolute_unchanged(self, tmp_path: Path) -> None:
        cache = CacheConfig(path=tmp_path)
        assert cache.resolved_path == tmp_path


class TestCacheConfigValidation:
    def test_ttl_hours_minimum_is_1(self) -> None:
        with pytest.raises(ValidationError):
            CacheConfig(ttl_hours=0)

    def test_alarm_minutes_minimum_is_0(self) -> None:
        IcsConfig(alarm_minutes=0)  # doit passer sans exception

    def test_alarm_minutes_negative_raises(self) -> None:
        with pytest.raises(ValidationError):
            IcsConfig(alarm_minutes=-1)


class TestProvidersConfigDefaults:
    def test_formula1_and_wec_have_independent_defaults(self) -> None:
        config = ProvidersConfig()
        assert config.formula1.source != config.wec.source

    def test_provider_config_enabled_true_by_default(self) -> None:
        assert ProviderConfig(source="openf1").enabled is True

    def test_provider_config_can_be_disabled(self) -> None:
        assert ProviderConfig(source="openf1", enabled=False).enabled is False

    def test_providers_config_get_formula1_returns_correct_config(self) -> None:
        config = ProvidersConfig()
        pc = config.get("formula1")
        assert pc is not None
        assert pc.source == "openf1"

    def test_providers_config_get_wec_returns_correct_config(self) -> None:
        config = ProvidersConfig()
        pc = config.get("wec")
        assert pc is not None
        assert pc.source == "official"

    def test_providers_config_get_unknown_returns_none(self) -> None:
        config = ProvidersConfig()
        assert config.get("f2") is None

    def test_providers_config_get_extra_from_yaml(self) -> None:
        """Un provider extra (non nommé) défini dans le YAML est accessible via get()."""
        config = ProvidersConfig.model_validate(
            {"formula1": {"source": "openf1"}, "f2": {"enabled": False}}
        )
        pc = config.get("f2")
        assert pc is not None
        assert pc.enabled is False


class TestUpdateConfig:
    def test_default_manifest_url_is_empty(self) -> None:
        assert UpdateConfig().manifest_url == ""

    def test_manifest_url_accepts_any_host(self) -> None:
        """Sprint 51 — no validation ties this to a specific platform;
        any absolute URL is accepted as-is."""
        config = UpdateConfig(manifest_url="https://updates.example.org/latest.json")
        assert config.manifest_url == "https://updates.example.org/latest.json"

    def test_is_frozen(self) -> None:
        config = UpdateConfig()
        with pytest.raises(ValidationError):
            config.manifest_url = "https://changed.test"


# ---------------------------------------------------------------------------
# ConfigService — pas de fichier
# ---------------------------------------------------------------------------


class TestConfigServiceDefaultPaths:
    """Sprint 49 — the user-level config.yaml lookup path must be the
    platform user config directory, never a hardcoded Linux-only path."""

    def test_second_default_path_is_user_config_dir(self) -> None:
        expected = user_config_dir("motorsport-calendar") / "config.yaml"
        assert ConfigService._DEFAULT_PATHS[1] == expected

    def test_first_default_path_is_still_cwd_relative(self) -> None:
        """The CWD-relative ``config.yaml`` lookup is an intentional,
        read-only convenience (project-local override) — not a packaging
        bug, left unchanged."""
        assert ConfigService._DEFAULT_PATHS[0] == Path("config.yaml")


class TestConfigServiceNoFile:
    def test_returns_defaults_when_file_missing(self, tmp_path: Path) -> None:
        svc = ConfigService(config_path=tmp_path / "nonexistent.yaml")
        assert svc.config == AppConfig()

    def test_timezone_is_paris_by_default(self, tmp_path: Path) -> None:
        svc = ConfigService(config_path=tmp_path / "nonexistent.yaml")
        assert svc.timezone == "Europe/Paris"

    def test_cache_enabled_by_default(self, tmp_path: Path) -> None:
        svc = ConfigService(config_path=tmp_path / "nonexistent.yaml")
        assert svc.cache.enabled is True

    def test_alarm_minutes_30_by_default(self, tmp_path: Path) -> None:
        svc = ConfigService(config_path=tmp_path / "nonexistent.yaml")
        assert svc.ics.alarm_minutes == 30

    def test_update_manifest_url_empty_by_default(self, tmp_path: Path) -> None:
        svc = ConfigService(config_path=tmp_path / "nonexistent.yaml")
        assert svc.update.manifest_url == ""


# ---------------------------------------------------------------------------
# ConfigService — lecture YAML
# ---------------------------------------------------------------------------


class TestConfigServiceYaml:
    def test_reads_timezone(self, tmp_path: Path) -> None:
        cfg = tmp_path / "config.yaml"
        cfg.write_text("timezone: America/New_York\n", encoding="utf-8")
        svc = ConfigService(config_path=cfg)
        assert svc.timezone == "America/New_York"

    def test_reads_cache_enabled_false(self, tmp_path: Path) -> None:
        cfg = tmp_path / "config.yaml"
        cfg.write_text("cache:\n  enabled: false\n", encoding="utf-8")
        svc = ConfigService(config_path=cfg)
        assert svc.cache.enabled is False

    def test_reads_cache_ttl_hours(self, tmp_path: Path) -> None:
        cfg = tmp_path / "config.yaml"
        cfg.write_text("cache:\n  ttl_hours: 48\n", encoding="utf-8")
        svc = ConfigService(config_path=cfg)
        assert svc.cache.ttl_hours == 48

    def test_reads_cache_path(self, tmp_path: Path) -> None:
        cfg = tmp_path / "config.yaml"
        cfg.write_text(f"cache:\n  path: {tmp_path}\n", encoding="utf-8")
        svc = ConfigService(config_path=cfg)
        assert svc.cache.path == tmp_path

    def test_reads_ics_alarm_minutes(self, tmp_path: Path) -> None:
        cfg = tmp_path / "config.yaml"
        cfg.write_text("ics:\n  alarm_minutes: 15\n", encoding="utf-8")
        svc = ConfigService(config_path=cfg)
        assert svc.ics.alarm_minutes == 15

    def test_reads_f1_source(self, tmp_path: Path) -> None:
        cfg = tmp_path / "config.yaml"
        cfg.write_text("providers:\n  formula1:\n    source: ergast\n", encoding="utf-8")
        svc = ConfigService(config_path=cfg)
        assert svc.providers.formula1.source == "ergast"

    def test_reads_wec_source(self, tmp_path: Path) -> None:
        cfg = tmp_path / "config.yaml"
        cfg.write_text("providers:\n  wec:\n    source: custom\n", encoding="utf-8")
        svc = ConfigService(config_path=cfg)
        assert svc.providers.wec.source == "custom"

    def test_reads_update_manifest_url(self, tmp_path: Path) -> None:
        cfg = tmp_path / "config.yaml"
        cfg.write_text(
            "update:\n  manifest_url: https://example.test/manifest.json\n",
            encoding="utf-8",
        )
        svc = ConfigService(config_path=cfg)
        assert svc.update.manifest_url == "https://example.test/manifest.json"

    def test_reads_full_config(self, tmp_path: Path) -> None:
        cfg = tmp_path / "config.yaml"
        cfg.write_text(
            "timezone: Asia/Tokyo\n"
            "cache:\n  enabled: true\n  ttl_hours: 12\n"
            "ics:\n  alarm_minutes: 60\n"
            "providers:\n  formula1:\n    source: openf1\n  wec:\n    source: official\n",
            encoding="utf-8",
        )
        svc = ConfigService(config_path=cfg)
        assert svc.timezone == "Asia/Tokyo"
        assert svc.cache.ttl_hours == 12
        assert svc.ics.alarm_minutes == 60
        assert svc.providers.formula1.source == "openf1"


# ---------------------------------------------------------------------------
# ConfigService — fusion avec les défauts (YAML partiel)
# ---------------------------------------------------------------------------


class TestConfigServicePartialYaml:
    def test_partial_cache_uses_defaults_for_missing_fields(self, tmp_path: Path) -> None:
        cfg = tmp_path / "config.yaml"
        cfg.write_text("cache:\n  ttl_hours: 48\n", encoding="utf-8")
        svc = ConfigService(config_path=cfg)
        assert svc.cache.ttl_hours == 48
        assert svc.cache.enabled is True  # défaut préservé

    def test_partial_providers_uses_defaults_for_missing_provider(self, tmp_path: Path) -> None:
        cfg = tmp_path / "config.yaml"
        cfg.write_text("providers:\n  formula1:\n    source: ergast\n", encoding="utf-8")
        svc = ConfigService(config_path=cfg)
        assert svc.providers.formula1.source == "ergast"
        assert svc.providers.wec.source == "official"  # défaut préservé

    def test_empty_yaml_uses_all_defaults(self, tmp_path: Path) -> None:
        cfg = tmp_path / "config.yaml"
        cfg.write_text("", encoding="utf-8")
        svc = ConfigService(config_path=cfg)
        assert svc.config == AppConfig()
