"""Tests for GUI preferences module — no Flet dependency."""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from motorsport_calendar.gui import preferences
from motorsport_calendar.gui.preferences import load_preferences, save_preferences


class TestDefaultPrefsFileLocation:
    """Sprint 49 — the module-level default must be computed from the
    platform user config directory, never a hardcoded Linux-only path.

    Source-inspection rather than reading the live ``_PREFS_FILE``
    attribute: the autouse ``_isolated_gui_prefs`` fixture (conftest.py)
    always overrides it during tests, by design, so every test — this one
    included — never touches the real machine's preferences file.
    """

    def test_prefs_file_is_computed_via_user_config_dir(self) -> None:
        source = inspect.getsource(preferences)
        assert 'user_config_dir("motorsport-calendar")' in source
        assert '.home() / ".config"' not in source  # the old, Linux-only literal


class TestLoadPreferences:
    def test_returns_defaults_on_first_run(self, tmp_path: Path) -> None:
        fake_file = tmp_path / "nonexistent" / "prefs.json"
        with patch("motorsport_calendar.gui.preferences._PREFS_FILE", fake_file):
            prefs = load_preferences()
        assert prefs["selected_championships"] == ["formula1"]

    def test_returns_saved_values(self, tmp_path: Path) -> None:
        prefs_file = tmp_path / "gui_prefs.json"
        prefs_file.write_text(
            json.dumps({"selected_championships": ["formula2", "formula3"]}),
            encoding="utf-8",
        )
        with patch("motorsport_calendar.gui.preferences._PREFS_FILE", prefs_file):
            prefs = load_preferences()
        assert prefs["selected_championships"] == ["formula2", "formula3"]

    def test_merges_with_defaults_for_new_keys(self, tmp_path: Path) -> None:
        prefs_file = tmp_path / "gui_prefs.json"
        prefs_file.write_text(
            json.dumps({"selected_championships": ["formula1"]}),
            encoding="utf-8",
        )
        with patch("motorsport_calendar.gui.preferences._PREFS_FILE", prefs_file):
            prefs = load_preferences()
        assert "last_output_dir" in prefs

    def test_favorite_championships_defaults_to_empty_list(self, tmp_path: Path) -> None:
        """Sprint 44 — FavoritesService relies on this default being an
        empty list, not a missing key, on first run."""
        fake_file = tmp_path / "nonexistent" / "prefs.json"
        with patch("motorsport_calendar.gui.preferences._PREFS_FILE", fake_file):
            prefs = load_preferences()
        assert prefs["favorite_championships"] == []

    def test_favorite_championships_preserved_alongside_other_keys(self, tmp_path: Path) -> None:
        prefs_file = tmp_path / "gui_prefs.json"
        prefs_file.write_text(
            json.dumps(
                {
                    "selected_championships": ["formula1"],
                    "favorite_championships": ["wec", "motogp"],
                }
            ),
            encoding="utf-8",
        )
        with patch("motorsport_calendar.gui.preferences._PREFS_FILE", prefs_file):
            prefs = load_preferences()
        assert prefs["favorite_championships"] == ["wec", "motogp"]
        assert prefs["selected_championships"] == ["formula1"]

    def test_notifications_defaults_on_first_run(self, tmp_path: Path) -> None:
        """Sprint 46 — NotificationService relies on these 3 defaults being
        present, not missing keys, on first run."""
        fake_file = tmp_path / "nonexistent" / "prefs.json"
        with patch("motorsport_calendar.gui.preferences._PREFS_FILE", fake_file):
            prefs = load_preferences()
        assert prefs["notifications_enabled"] is False
        assert prefs["notifications_default_lead_time_minutes"] == 60
        assert prefs["notifications_favorites_only"] is False

    def test_notifications_keys_preserved_alongside_other_keys(self, tmp_path: Path) -> None:
        prefs_file = tmp_path / "gui_prefs.json"
        prefs_file.write_text(
            json.dumps(
                {
                    "selected_championships": ["formula1"],
                    "notifications_enabled": True,
                    "notifications_default_lead_time_minutes": 15,
                    "notifications_favorites_only": True,
                }
            )
        )
        with patch("motorsport_calendar.gui.preferences._PREFS_FILE", prefs_file):
            prefs = load_preferences()
        assert prefs["notifications_enabled"] is True
        assert prefs["notifications_default_lead_time_minutes"] == 15
        assert prefs["notifications_favorites_only"] is True
        assert prefs["selected_championships"] == ["formula1"]

    def test_update_check_enabled_defaults_to_true_on_first_run(self, tmp_path: Path) -> None:
        """Sprint 51 — checking is opt-out, not opt-in: a first-run user
        who never touched preferences still gets checked."""
        fake_file = tmp_path / "nonexistent" / "prefs.json"
        with patch("motorsport_calendar.gui.preferences._PREFS_FILE", fake_file):
            prefs = load_preferences()
        assert prefs["update_check_enabled"] is True

    def test_update_check_enabled_preserved_alongside_other_keys(self, tmp_path: Path) -> None:
        prefs_file = tmp_path / "gui_prefs.json"
        prefs_file.write_text(
            json.dumps({"selected_championships": ["formula1"], "update_check_enabled": False})
        )
        with patch("motorsport_calendar.gui.preferences._PREFS_FILE", prefs_file):
            prefs = load_preferences()
        assert prefs["update_check_enabled"] is False
        assert prefs["selected_championships"] == ["formula1"]

    def test_default_year_defaults_to_current_sentinel_on_first_run(self, tmp_path: Path) -> None:
        """Sprint 52 — "current" never goes stale, unlike a baked-in year."""
        fake_file = tmp_path / "nonexistent" / "prefs.json"
        with patch("motorsport_calendar.gui.preferences._PREFS_FILE", fake_file):
            prefs = load_preferences()
        assert prefs["default_year"] == "current"

    def test_default_year_preserved_alongside_other_keys(self, tmp_path: Path) -> None:
        prefs_file = tmp_path / "gui_prefs.json"
        prefs_file.write_text(
            json.dumps({"selected_championships": ["formula1"], "default_year": "2027"})
        )
        with patch("motorsport_calendar.gui.preferences._PREFS_FILE", prefs_file):
            prefs = load_preferences()
        assert prefs["default_year"] == "2027"
        assert prefs["selected_championships"] == ["formula1"]

    def test_ics_alarm_minutes_defaults_to_30_on_first_run(self, tmp_path: Path) -> None:
        """Sprint 52 — matches config/models.py::IcsConfig's own default
        (30), so a user who never opens Préférences sees identical
        exported .ics files to before this sprint."""
        fake_file = tmp_path / "nonexistent" / "prefs.json"
        with patch("motorsport_calendar.gui.preferences._PREFS_FILE", fake_file):
            prefs = load_preferences()
        assert prefs["ics_alarm_minutes"] == 30

    def test_ics_alarm_minutes_preserved_alongside_other_keys(self, tmp_path: Path) -> None:
        prefs_file = tmp_path / "gui_prefs.json"
        prefs_file.write_text(
            json.dumps({"selected_championships": ["formula1"], "ics_alarm_minutes": 15})
        )
        with patch("motorsport_calendar.gui.preferences._PREFS_FILE", prefs_file):
            prefs = load_preferences()
        assert prefs["ics_alarm_minutes"] == 15
        assert prefs["selected_championships"] == ["formula1"]

    def test_handles_corrupted_json(self, tmp_path: Path) -> None:
        prefs_file = tmp_path / "gui_prefs.json"
        prefs_file.write_text("NOT_JSON {{{{", encoding="utf-8")
        with patch("motorsport_calendar.gui.preferences._PREFS_FILE", prefs_file):
            prefs = load_preferences()
        assert prefs["selected_championships"] == ["formula1"]

    def test_returns_dict(self, tmp_path: Path) -> None:
        fake_file = tmp_path / "prefs.json"
        with patch("motorsport_calendar.gui.preferences._PREFS_FILE", fake_file):
            prefs = load_preferences()
        assert isinstance(prefs, dict)


class TestSavePreferences:
    def test_roundtrip(self, tmp_path: Path) -> None:
        prefs_file = tmp_path / "sub" / "gui_prefs.json"
        data = {"selected_championships": ["formula3"], "last_output_dir": ""}
        with patch("motorsport_calendar.gui.preferences._PREFS_FILE", prefs_file):
            save_preferences(data)
            loaded = load_preferences()
        assert loaded["selected_championships"] == ["formula3"]

    def test_creates_parent_dirs(self, tmp_path: Path) -> None:
        deep = tmp_path / "a" / "b" / "c" / "prefs.json"
        with patch("motorsport_calendar.gui.preferences._PREFS_FILE", deep):
            save_preferences({"selected_championships": ["formula1"], "last_output_dir": ""})
        assert deep.exists()

    def test_file_content_is_valid_json(self, tmp_path: Path) -> None:
        prefs_file = tmp_path / "gui_prefs.json"
        data = {"selected_championships": ["formula2"], "last_output_dir": "/tmp"}
        with patch("motorsport_calendar.gui.preferences._PREFS_FILE", prefs_file):
            save_preferences(data)
        content = prefs_file.read_text(encoding="utf-8")
        parsed = json.loads(content)
        assert parsed["selected_championships"] == ["formula2"]

    def test_os_error_is_swallowed(self) -> None:
        mock_path = MagicMock(spec=Path)
        mock_path.parent.mkdir = MagicMock()
        mock_path.write_text = MagicMock(side_effect=OSError("disk full"))
        with patch("motorsport_calendar.gui.preferences._PREFS_FILE", mock_path):
            save_preferences({"selected_championships": []})  # must not raise
