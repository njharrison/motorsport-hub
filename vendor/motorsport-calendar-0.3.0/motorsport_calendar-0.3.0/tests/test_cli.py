"""Tests for the CLI entry point."""

from typer.testing import CliRunner

from motorsport_calendar import __version__
from motorsport_calendar.cli import app

runner = CliRunner()


class TestHelp:
    def test_help_exits_zero(self) -> None:
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0

    def test_help_contains_app_name(self) -> None:
        result = runner.invoke(app, ["--help"])
        assert "motocal" in result.output or "motorsport" in result.output.lower()


class TestVersion:
    def test_version_command(self) -> None:
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert __version__ in result.output

    def test_version_flag(self) -> None:
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert __version__ in result.output


class TestProviders:
    def test_providers_command_exits_zero(self) -> None:
        result = runner.invoke(app, ["providers"])
        assert result.exit_code == 0


class TestExportCommandRemoved:
    """MC-002 (P0-3): the CLI's `export` command was a permanent stub that
    always failed (see removed `TestExport` class) — a real, documented
    public command that could never succeed (MC-001 §4, P0 blocker).
    Removed entirely rather than hidden: it never had any implementation
    to preserve. `generate`/`generate-*` are the real, working commands."""

    def test_export_is_not_a_registered_command(self) -> None:
        result = runner.invoke(app, ["export"])
        assert result.exit_code != 0
        assert "No such command" in result.output
