"""Tests for the championship visual identity registry (Sprint 33).

``get_championship_asset()`` is the single entry point every view/component
must use instead of hardcoding a file path or special-casing a championship
id. No file exists in the real ``gui/assets/championships/`` directory yet,
so these tests monkeypatch the module's ``_ASSETS_DIR`` to a temporary
directory to exercise the "logo present" branch without touching the repo.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from motorsport_calendar.gui import championship_assets
from motorsport_calendar.gui.championship_assets import (
    ChampionshipAsset,
    get_championship_asset,
)


class TestChampionshipAsset:
    def test_is_frozen(self) -> None:
        asset = ChampionshipAsset(logo_src=None)
        with pytest.raises(AttributeError):
            asset.logo_src = "championships/formula1.png"  # type: ignore[misc]


class TestNoLogoDeliveredYet:
    """The real repository ships no championship logo files today — every
    known id must resolve to `logo_src=None`, never an exception."""

    @pytest.mark.parametrize(
        "championship_id",
        ["formula1", "formula2", "formula3", "f1-academy", "wec"],
    )
    def test_known_id_without_delivered_file_has_no_logo(self, championship_id: str) -> None:
        asset = get_championship_asset(championship_id)
        assert asset.logo_src is None


class TestUnknownChampionship:
    def test_unknown_id_has_no_logo_and_does_not_raise(self) -> None:
        asset = get_championship_asset("nascar")
        assert asset == ChampionshipAsset(logo_src=None)

    def test_empty_id_has_no_logo_and_does_not_raise(self) -> None:
        asset = get_championship_asset("")
        assert asset.logo_src is None


class TestLogoDelivered:
    """Simulates a logo file having been dropped in place — the only
    scenario that produces a non-None `logo_src`."""

    def test_known_id_with_delivered_file_resolves_to_asset_relative_path(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(championship_assets, "_ASSETS_DIR", tmp_path)
        (tmp_path / "formula1.png").touch()

        asset = get_championship_asset("formula1")

        assert asset.logo_src == "championships/formula1.png"

    def test_only_the_delivered_file_resolves_siblings_stay_none(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(championship_assets, "_ASSETS_DIR", tmp_path)
        (tmp_path / "formula1.png").touch()

        assert get_championship_asset("formula1").logo_src is not None
        assert get_championship_asset("formula2").logo_src is None

    def test_unknown_id_still_has_no_logo_even_if_directory_is_populated(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(championship_assets, "_ASSETS_DIR", tmp_path)
        (tmp_path / "formula1.png").touch()

        assert get_championship_asset("nascar").logo_src is None
