"""Packaging integrity tests.

Verify that the installed package is correctly wired:
- importlib.metadata version matches __version__
- __main__.py entry point works (python -m motorsport_calendar)
- All CLI commands are registered in the Typer app
- Key public API imports succeed
- Providers and sources auto-register correctly
"""

from __future__ import annotations

import importlib
import importlib.metadata
from pathlib import Path
import subprocess
import sys
import tomllib

import pytest
from typer.testing import CliRunner

from motorsport_calendar import __version__
from motorsport_calendar.cli import app

runner = CliRunner()

_REPO_ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Package metadata
# ---------------------------------------------------------------------------


class TestPackageMetadata:
    def test_version_is_defined(self) -> None:
        assert __version__ is not None
        assert isinstance(__version__, str)
        assert len(__version__) > 0

    def test_version_matches_metadata(self) -> None:
        metadata_version = importlib.metadata.version("motorsport-calendar")
        assert __version__ == metadata_version

    def test_version_is_semver(self) -> None:
        parts = __version__.split(".")
        assert len(parts) == 3
        assert all(p.isdigit() for p in parts)

    def test_package_importable(self) -> None:
        mod = importlib.import_module("motorsport_calendar")
        assert mod is not None

    def test_author_defined(self) -> None:
        from motorsport_calendar import __author__

        assert __author__


# ---------------------------------------------------------------------------
# Entry point — python -m motorsport_calendar
# ---------------------------------------------------------------------------


class TestMainEntryPoint:
    def test_python_m_help_exits_zero(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "motorsport_calendar", "--help"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        assert result.returncode == 0

    def test_python_m_help_shows_usage(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "motorsport_calendar", "--help"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        assert "usage" in result.stdout.lower() or "motocal" in result.stdout.lower()

    def test_python_m_version_exits_zero(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "motorsport_calendar", "version"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        assert result.returncode == 0

    def test_python_m_version_shows_version(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "motorsport_calendar", "version"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        assert __version__ in result.stdout

    def test_python_m_providers_exits_zero(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "motorsport_calendar", "providers"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        assert result.returncode == 0


# ---------------------------------------------------------------------------
# CLI commands registered
# ---------------------------------------------------------------------------


class TestCLICommands:
    def test_help_shows_generate_f1(self) -> None:
        result = runner.invoke(app, ["--help"])
        assert "generate-f1" in result.output

    def test_help_shows_generate_f2(self) -> None:
        result = runner.invoke(app, ["--help"])
        assert "generate-f2" in result.output

    def test_help_shows_generate_f3(self) -> None:
        result = runner.invoke(app, ["--help"])
        assert "generate-f3" in result.output

    def test_help_shows_generate_f1_academy(self) -> None:
        result = runner.invoke(app, ["--help"])
        assert "generate-f1-academy" in result.output

    def test_help_shows_generate_wec(self) -> None:
        result = runner.invoke(app, ["--help"])
        assert "generate-wec" in result.output

    def test_help_shows_generate(self) -> None:
        result = runner.invoke(app, ["--help"])
        assert "generate" in result.output

    def test_help_shows_providers(self) -> None:
        result = runner.invoke(app, ["--help"])
        assert "providers" in result.output

    def test_help_shows_version(self) -> None:
        result = runner.invoke(app, ["--help"])
        assert "version" in result.output

    def test_version_command_output_contains_version(self) -> None:
        result = runner.invoke(app, ["version"])
        assert __version__ in result.output
        assert result.exit_code == 0

    def test_providers_command_lists_formula1(self) -> None:
        result = runner.invoke(app, ["providers"])
        assert "formula1" in result.output
        assert result.exit_code == 0

    def test_providers_command_lists_formula2(self) -> None:
        result = runner.invoke(app, ["providers"])
        assert "formula2" in result.output

    def test_providers_command_lists_formula3(self) -> None:
        result = runner.invoke(app, ["providers"])
        assert "formula3" in result.output

    def test_providers_command_lists_f1_academy(self) -> None:
        result = runner.invoke(app, ["providers"])
        assert "f1-academy" in result.output

    def test_providers_command_lists_wec(self) -> None:
        result = runner.invoke(app, ["providers"])
        assert "wec" in result.output


# ---------------------------------------------------------------------------
# Public API imports
# ---------------------------------------------------------------------------


class TestPublicImports:
    def test_models_importable(self) -> None:
        from motorsport_calendar.models import (
            Championship,
            ChampionshipCategory,
            Circuit,
            Event,
            Session,
            SessionType,
        )

        assert Championship is not None
        assert ChampionshipCategory is not None
        assert Circuit is not None
        assert Event is not None
        assert Session is not None
        assert SessionType is not None

    def test_datasource_importable(self) -> None:
        from motorsport_calendar.core.datasource import (
            DataSource,
            HtmlDataSource,
            IcsDataSource,
            JsonDataSource,
        )

        assert DataSource is not None
        assert JsonDataSource is not None
        assert HtmlDataSource is not None
        assert IcsDataSource is not None

    def test_registry_importable(self) -> None:
        from motorsport_calendar.core import registry, source_registry

        assert registry is not None
        assert source_registry is not None

    def test_formula1_provider_importable(self) -> None:
        from motorsport_calendar.providers.formula1 import Formula1Provider, Formula1Source

        assert Formula1Provider is not None
        assert Formula1Source is not None

    def test_formula2_provider_importable(self) -> None:
        from motorsport_calendar.providers.formula2 import Formula2Provider, Formula2Source

        assert Formula2Provider is not None
        assert Formula2Source is not None

    def test_formula3_provider_importable(self) -> None:
        from motorsport_calendar.providers.formula3 import Formula3Provider, Formula3Source

        assert Formula3Provider is not None
        assert Formula3Source is not None

    def test_f1_academy_provider_importable(self) -> None:
        from motorsport_calendar.providers.f1_academy import F1AcademyProvider, F1AcademySource

        assert F1AcademyProvider is not None
        assert F1AcademySource is not None

    def test_support_series_base_importable(self) -> None:
        from motorsport_calendar.providers.support_series.f1calendar_base import (
            F1CalendarBaseSource,
        )

        assert F1CalendarBaseSource is not None

    def test_wec_provider_importable(self) -> None:
        from motorsport_calendar.providers.wec import WecProvider, WecSource

        assert WecProvider is not None
        assert WecSource is not None

    def test_ics_exporter_importable(self) -> None:
        from motorsport_calendar.exporters.ics import IcsExporter

        assert IcsExporter is not None

    def test_http_cache_importable(self) -> None:
        from motorsport_calendar.cache import HttpCache

        assert HttpCache is not None

    def test_config_service_importable(self) -> None:
        from motorsport_calendar.config import ConfigService

        assert ConfigService is not None

    def test_utils_paths_importable(self) -> None:
        from motorsport_calendar.utils.paths import user_cache_dir, user_config_dir

        assert user_cache_dir is not None
        assert user_config_dir is not None


# ---------------------------------------------------------------------------
# GUI assets — Sprint 49 (Brand Set v1.0, Flet assets_dir bundling)
# ---------------------------------------------------------------------------


class TestGuiAssetsBundling:
    """gui.app is importable without Flet actually being installed as a
    hard dependency (it's an optional extra) — only the module-level
    ``_ASSETS_DIR`` constant is exercised here, never ``main()`` itself
    (which imports flet lazily, inside the function body)."""

    def test_gui_app_importable(self) -> None:
        from motorsport_calendar.gui import app

        assert app is not None

    def test_assets_dir_is_absolute(self) -> None:
        from motorsport_calendar.gui.app import _ASSETS_DIR

        assert Path(_ASSETS_DIR).is_absolute()

    def test_assets_dir_exists_and_contains_official_brand_files(self) -> None:
        from motorsport_calendar.gui.app import _ASSETS_DIR

        assets = Path(_ASSETS_DIR)
        assert assets.is_dir()
        # The exact 6 files named in the Sprint 49 brief.
        assert (assets / "icon.png").is_file()
        assert (assets / "icon_windows.ico").is_file()
        assert (assets / "favicon-16.png").is_file()
        assert (assets / "favicon-32.png").is_file()
        assert (assets / "logo" / "mc-icon.svg").is_file()
        assert (assets / "logo" / "logo-horizontal.svg").is_file()
        assert (assets / "logo" / "logo-vertical.svg").is_file()

    def test_assets_dir_resolution_is_independent_of_cwd(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Sprint 49 — Flet's own ``assets_dir`` resolves relative strings
        against the CWD at launch time, not this module's location — a
        packaged/installed ``motocal-gui`` can be launched from anywhere.
        ``_ASSETS_DIR`` must already be an absolute path so it never
        depends on the launch directory."""
        monkeypatch.chdir(tmp_path)
        import importlib

        from motorsport_calendar.gui import app

        importlib.reload(app)
        assert Path(app._ASSETS_DIR).is_dir()


# ---------------------------------------------------------------------------
# Registry auto-discovery
# ---------------------------------------------------------------------------


class TestRegistryDiscovery:
    """Tests use the application singletons — discover() populates the shared registry."""

    def test_discover_registers_formula1(self) -> None:
        from motorsport_calendar.core.registry import registry

        registry.discover()
        assert "formula1" in registry.list_all()

    def test_discover_registers_formula2(self) -> None:
        from motorsport_calendar.core.registry import registry

        registry.discover()
        assert "formula2" in registry.list_all()

    def test_discover_registers_formula3(self) -> None:
        from motorsport_calendar.core.registry import registry

        registry.discover()
        assert "formula3" in registry.list_all()

    def test_discover_registers_f1_academy(self) -> None:
        from motorsport_calendar.core.registry import registry

        registry.discover()
        assert "f1-academy" in registry.list_all()

    def test_discover_registers_wec(self) -> None:
        from motorsport_calendar.core.registry import registry

        registry.discover()
        assert "wec" in registry.list_all()

    def test_source_discover_registers_openf1(self) -> None:
        from motorsport_calendar.core.source_registry import source_registry

        source_registry.discover()
        assert "openf1" in source_registry.list_for("formula1")

    def test_source_discover_registers_jolpica(self) -> None:
        from motorsport_calendar.core.source_registry import source_registry

        source_registry.discover()
        assert "jolpica" in source_registry.list_for("formula1")

    def test_source_discover_registers_f1calendar_formula2(self) -> None:
        from motorsport_calendar.core.source_registry import source_registry

        source_registry.discover()
        assert "f1calendar" in source_registry.list_for("formula2")

    def test_source_discover_registers_f1calendar_formula3(self) -> None:
        from motorsport_calendar.core.source_registry import source_registry

        source_registry.discover()
        assert "f1calendar" in source_registry.list_for("formula3")

    def test_source_discover_registers_f1calendar_f1_academy(self) -> None:
        from motorsport_calendar.core.source_registry import source_registry

        source_registry.discover()
        assert "f1calendar" in source_registry.list_for("f1-academy")


# ---------------------------------------------------------------------------
# Flet build manifest — Sprint 58/59 (Validation & correction packaging)
# ---------------------------------------------------------------------------


def _parse_requirement_name(requirement: str) -> str:
    """Package name only, stripped of any version specifier — e.g.
    ``"pydantic>=2.7"`` -> ``"pydantic"``. Good enough for this file's own
    dependency strings (no extras, no markers, no `@` URLs)."""
    for sep in ("==", ">=", "<=", "~=", ">", "<", "!="):
        if sep in requirement:
            return requirement.split(sep, 1)[0].strip()
    return requirement.strip()


class TestFletBuildManifest:
    """``motorsport_calendar/gui/pyproject.toml`` (Sprint 58/59) is a
    second, build-only manifest — the one ``flet build linux
    motorsport_calendar/gui --module-name app`` actually reads (Flet
    loads ``pyproject.toml`` from the exact directory it's pointed at,
    confirmed by reading ``flet_cli``'s own source — never the repo
    root). Without it, the compiled app crashed on startup with
    ``ModuleNotFoundError: No module named 'motorsport_calendar'`` — and
    fixing *only* the missing-dependencies half of that (a naive
    duplicate ``[project.dependencies]`` list here) was proven
    insufficient by an actual rebuild + a real launch of the compiled
    binary: the app still crashed the same way, because `flet build`
    zips the *contents* of whichever directory it's pointed at
    (`motorsport_calendar/gui/`'s own files, flattened, no
    `motorsport_calendar.` package wrapper) — no dependency list fixes
    that on its own, since every file in `gui/` uses absolute
    ``from motorsport_calendar.gui... import`` statements.

    The actual fix: ``tool.flet.dev_packages`` installs this project
    itself, from its real root, as a genuine local package — the exact
    mechanism Flet provides for "a dependency I'm developing locally,
    not on PyPI". This is why the build manifest's own
    ``[project.dependencies]`` lists only ``flet`` + ``motorsport-
    calendar`` itself, never a duplicated copy of the root's 9 real
    dependencies — installing the local package pulls those in
    transitively, from the one place they're actually declared."""

    @pytest.fixture()
    def root_pyproject(self) -> dict:
        return tomllib.loads((_REPO_ROOT / "pyproject.toml").read_text())

    @pytest.fixture()
    def gui_pyproject(self) -> dict:
        return tomllib.loads(
            (_REPO_ROOT / "motorsport_calendar" / "gui" / "pyproject.toml").read_text()
        )

    def test_gui_manifest_exists(self) -> None:
        assert (_REPO_ROOT / "motorsport_calendar" / "gui" / "pyproject.toml").is_file()

    def test_gui_manifest_declares_flet(self, gui_pyproject: dict) -> None:
        """``flet`` itself is only an optional extra at the root (CLI-only
        installs must never require it) — the build manifest is the one
        place it must be a hard dependency, or the compiled app has no
        Flet to import either."""
        names = {_parse_requirement_name(d) for d in gui_pyproject["project"]["dependencies"]}
        assert "flet" in names

    def test_gui_manifest_declares_the_project_itself(
        self, root_pyproject: dict, gui_pyproject: dict
    ) -> None:
        """The one dependency that actually pulls in `motorsport_calendar`
        (the real package, correctly nested) plus every one of its own
        declared dependencies transitively — never a second, duplicated
        copy of that dependency list in this file."""
        names = {_parse_requirement_name(d) for d in gui_pyproject["project"]["dependencies"]}
        assert root_pyproject["project"]["name"] in names

    def test_gui_manifest_never_duplicates_the_root_dependency_list(
        self, root_pyproject: dict, gui_pyproject: dict
    ) -> None:
        """The single-source-of-truth guarantee: nothing here should name
        one of the root's own runtime dependencies directly — if one
        shows up, someone reintroduced the duplicated-list pattern this
        design deliberately avoids (harmless today, but a future edit to
        one list silently drifting from the other is exactly the
        fragility the brief asked not to create)."""
        root_names = {_parse_requirement_name(d) for d in root_pyproject["project"]["dependencies"]}
        gui_names = {_parse_requirement_name(d) for d in gui_pyproject["project"]["dependencies"]}
        assert gui_names.isdisjoint(root_names)

    def test_gui_manifest_name_and_version_match_root(
        self, root_pyproject: dict, gui_pyproject: dict
    ) -> None:
        """Sprint 58's audit found the compiled app embedding Flet's own
        generic defaults (name ``"gui"``, version ``"1.0.0"``) instead of
        this project's real identity — both values come from whichever
        pyproject.toml `flet build` reads, so they must match the root."""
        assert gui_pyproject["project"]["name"] == root_pyproject["project"]["name"]
        assert gui_pyproject["project"]["version"] == root_pyproject["project"]["version"]

    def test_gui_manifest_pins_flutter_pubspec_version_to_root(
        self, root_pyproject: dict, gui_pyproject: dict
    ) -> None:
        """MC-002 (P0-5): `project.version` above is correctly read by
        `flet_cli` and passed as `--build-name` to `flutter build`, but
        that flag alone never updates the Flutter scaffold's own
        `pubspec.yaml` on disk — and Flutter's own build step generates
        `data/flutter_assets/version.json` by reading that file's
        `version:` line directly, not from `--build-name` (verified by
        reading Flet's installed source, not guessed — see this file's
        surrounding comment). `[tool.flet.flutter.pubspec]` is Flet's own
        supported extension point for overriding generated `pubspec.yaml`
        keys; asserting it here catches the exact regression that shipped
        `1.0.0` in the embedded build version (Sprint 59) if it ever
        drifts from `project.version` again. Flutter's pubspec format
        requires a trailing `+<build-number>` beyond plain semver, so this
        checks a prefix match, not equality."""
        flutter_pubspec_version = gui_pyproject["tool"]["flet"]["flutter"]["pubspec"]["version"]
        assert flutter_pubspec_version.startswith(f"{root_pyproject['project']['version']}+")

    def test_gui_manifest_declares_the_app_entry_module(self, gui_pyproject: dict) -> None:
        """``tool.flet.app.module`` makes the ``--module-name app`` CLI
        flag redundant (defense in depth, not a replacement — the
        documented build command still passes it explicitly)."""
        assert gui_pyproject["tool"]["flet"]["app"]["module"] == "app"

    def test_app_module_named_in_the_manifest_actually_exists(self, gui_pyproject: dict) -> None:
        module = gui_pyproject["tool"]["flet"]["app"]["module"]
        entry_point = _REPO_ROOT / "motorsport_calendar" / "gui" / f"{module}.py"
        assert entry_point.is_file()

    def test_dev_package_redirect_points_at_a_real_installable_project_root(
        self, gui_pyproject: dict
    ) -> None:
        """``tool.flet.dev_packages`` is what actually fixes the
        ``ModuleNotFoundError`` — resolved the same way `flet_cli` itself
        resolves it (relative to `motorsport_calendar/gui/`, since that's
        `python_app_path` in the documented build command), then checked
        against the real filesystem: the target must exist and be an
        installable project (its own `pyproject.toml` present)."""
        project_name = gui_pyproject["project"]["name"]
        dev_packages = gui_pyproject["tool"]["flet"]["dev_packages"]
        assert project_name in dev_packages

        gui_dir = _REPO_ROOT / "motorsport_calendar" / "gui"
        target = (gui_dir / dev_packages[project_name]).resolve()
        assert target == _REPO_ROOT
        assert (target / "pyproject.toml").is_file()
        assert (target / "motorsport_calendar" / "__init__.py").is_file()
