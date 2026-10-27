"""Tests for gui.favorites_service — no Flet dependency.

Isolated from the real preferences file by the autouse fixture in
tests/conftest.py (``_isolated_gui_prefs``) — every test here operates on
its own throwaway ``gui_prefs.json``.
"""

from __future__ import annotations

import json

from motorsport_calendar.gui import preferences
from motorsport_calendar.gui.favorites_service import FavoritesService
from motorsport_calendar.gui.preferences import load_preferences


class TestFavoritesServiceDefaults:
    def test_no_favorites_on_first_run(self) -> None:
        assert FavoritesService().list() == []

    def test_is_favorite_false_by_default(self) -> None:
        assert FavoritesService().is_favorite("formula1") is False


class TestFavoritesServiceAdd:
    def test_add_one_favorite(self) -> None:
        service = FavoritesService()
        service.add("formula1")
        assert service.list() == ["formula1"]

    def test_add_is_reflected_by_is_favorite(self) -> None:
        service = FavoritesService()
        service.add("formula1")
        assert service.is_favorite("formula1") is True
        assert service.is_favorite("motogp") is False

    def test_add_multiple_favorites_preserves_insertion_order(self) -> None:
        service = FavoritesService()
        service.add("formula1")
        service.add("motogp")
        service.add("wec")
        assert service.list() == ["formula1", "motogp", "wec"]

    def test_add_same_championship_twice_is_a_noop(self) -> None:
        service = FavoritesService()
        service.add("formula1")
        service.add("formula1")
        assert service.list() == ["formula1"]

    def test_add_persists_to_disk(self) -> None:
        FavoritesService().add("formula1")
        reloaded = FavoritesService()
        assert reloaded.list() == ["formula1"]


class TestFavoritesServiceRemove:
    def test_remove_a_favorite(self) -> None:
        service = FavoritesService()
        service.add("formula1")
        service.remove("formula1")
        assert service.list() == []

    def test_remove_leaves_other_favorites_untouched(self) -> None:
        service = FavoritesService()
        service.add("formula1")
        service.add("motogp")
        service.remove("formula1")
        assert service.list() == ["motogp"]

    def test_remove_non_favorite_is_a_noop(self) -> None:
        service = FavoritesService()
        service.add("formula1")
        service.remove("motogp")  # never favorited
        assert service.list() == ["formula1"]

    def test_remove_persists_to_disk(self) -> None:
        service = FavoritesService()
        service.add("formula1")
        service.add("motogp")
        service.remove("formula1")
        reloaded = FavoritesService()
        assert reloaded.list() == ["motogp"]


class TestFavoritesServiceToggle:
    def test_toggle_adds_when_not_favorited(self) -> None:
        service = FavoritesService()
        service.toggle("formula1")
        assert service.is_favorite("formula1") is True

    def test_toggle_removes_when_already_favorited(self) -> None:
        service = FavoritesService()
        service.add("formula1")
        service.toggle("formula1")
        assert service.is_favorite("formula1") is False

    def test_toggle_twice_returns_to_original_state(self) -> None:
        service = FavoritesService()
        service.toggle("formula1")
        service.toggle("formula1")
        assert service.list() == []


class TestFavoritesServicePersistenceAfterRestart:
    """Validation scenario from the brief: "persistance après redémarrage"
    — a fresh FavoritesService instance (simulating a new app launch) must
    see whatever the previous instance saved."""

    def test_survives_a_fresh_instance(self) -> None:
        first_session = FavoritesService()
        first_session.add("formula1")
        first_session.add("wec")

        second_session = FavoritesService()  # simulates app restart
        assert second_session.list() == ["formula1", "wec"]

    def test_empty_favorites_also_survive_a_fresh_instance(self) -> None:
        """ "aucun favori" validation scenario — an empty list is itself a
        valid, persisted state, not just the absence of a file."""
        first_session = FavoritesService()
        first_session.add("formula1")
        first_session.remove("formula1")

        second_session = FavoritesService()
        assert second_session.list() == []


class TestFavoritesServiceCentralizedPersistence:
    """The brief requires "la persistance doit être centralisée" — verifies
    FavoritesService shares gui_prefs.json with the rest of GUI state
    rather than using a second file, and never clobbers sibling keys."""

    def test_uses_the_shared_preferences_file(self) -> None:
        FavoritesService().add("formula1")
        assert preferences._PREFS_FILE.exists()
        on_disk = json.loads(preferences._PREFS_FILE.read_text(encoding="utf-8"))
        assert on_disk["favorite_championships"] == ["formula1"]

    def test_does_not_clobber_other_preference_keys(self) -> None:
        from motorsport_calendar.gui.preferences import save_preferences

        save_preferences({"selected_championships": ["formula2"], "last_output_dir": "/tmp"})
        FavoritesService().add("formula1")
        reloaded = load_preferences()
        assert reloaded["selected_championships"] == ["formula2"]
        assert reloaded["last_output_dir"] == "/tmp"
        assert reloaded["favorite_championships"] == ["formula1"]

    def test_favorites_saved_first_survive_a_later_selected_championships_save(self) -> None:
        """Mirrors main_view.py's own _save_prefs() read-modify-write fix
        — a favorite saved first must not be wiped by a later save of a
        different key."""
        from motorsport_calendar.gui.preferences import save_preferences

        FavoritesService().add("formula1")

        current = load_preferences()
        current["selected_championships"] = ["formula2"]
        save_preferences(current)

        assert load_preferences()["favorite_championships"] == ["formula1"]
