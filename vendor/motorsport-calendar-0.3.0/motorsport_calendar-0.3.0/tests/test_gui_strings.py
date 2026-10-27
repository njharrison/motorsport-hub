"""Tests for GUI strings module — no Flet dependency."""

from __future__ import annotations

from motorsport_calendar.gui.strings import STRINGS, Strings, plural


class TestStrings:
    def test_app_title(self) -> None:
        assert STRINGS.app_title == "Motorsport Calendar"

    def test_generate_btn_is_user_friendly(self) -> None:
        assert "Générer" not in STRINGS.generate_btn
        assert "calendrier" in STRINGS.generate_btn.lower()

    def test_all_required_keys_present(self) -> None:
        required = [
            "app_title",
            "app_subtitle",
            "season_label",
            "championships_label",
            "output_label",
            "output_hint",
            "browse_tooltip",
            "save_dialog_title",
            "generate_btn",
            "generating_status",
            "success_title",
            "success_saved_at",
            "open_folder_btn",
            "close_btn",
            "error_no_events",
            "error_unexpected",
            "summary_ok",
            "summary_error",
        ]
        for key in required:
            assert hasattr(STRINGS, key), f"Missing string key: {key}"

    def test_summary_ok_format(self) -> None:
        result = STRINGS.summary_ok.format(name="Formula 1", n=24, s="s")
        assert "Formula 1" in result
        assert "24" in result

    def test_summary_error_format(self) -> None:
        result = STRINGS.summary_error.format(name="FIA WEC", err="source non implémentée")
        assert "FIA WEC" in result
        assert "non implémentée" in result

    def test_error_unexpected_format(self) -> None:
        result = STRINGS.error_unexpected.format(msg="connexion refusée")
        assert "connexion refusée" in result

    def test_from_dict_overrides_key(self) -> None:
        s = Strings.from_dict({"app_title": "Custom App"})
        assert s.app_title == "Custom App"

    def test_from_dict_original_unchanged(self) -> None:
        Strings.from_dict({"app_title": "Custom App"})
        assert STRINGS.app_title == "Motorsport Calendar"

    def test_from_dict_unknown_key_ignored(self) -> None:
        s = Strings.from_dict({"_nonexistent_xyz_key": "value"})
        assert not hasattr(s, "_nonexistent_xyz_key")

    def test_from_dict_partial_override(self) -> None:
        s = Strings.from_dict({"close_btn": "OK"})
        assert s.close_btn == "OK"
        assert s.app_title == "Motorsport Calendar"

    def test_wizard_strings_removed(self) -> None:
        """Sprint 43: the 4-step wizard was replaced by a single
        reorganized page — every wizard_* string (step labels, nav
        buttons, recap rows) is gone with it."""
        for key in (
            "wizard_step_season",
            "wizard_step_championships",
            "wizard_step_destination",
            "wizard_step_create",
            "wizard_back_btn",
            "wizard_next_btn",
            "wizard_edit_btn",
            "wizard_recap_season",
            "wizard_recap_championships",
            "wizard_recap_destination",
            "wizard_recap_none",
            "wizard_title_season",
            "wizard_help_season",
            "wizard_title_championships",
            "wizard_help_championships",
            "wizard_title_destination",
            "wizard_help_destination",
            "wizard_title_create",
            "wizard_help_create",
        ):
            assert not hasattr(STRINGS, key), f"stale wizard string still present: {key}"

    def test_dead_backward_compat_nav_strings_removed(self) -> None:
        """Sprint 54 (Beta UX recette): nav_home/nav_calendar were never
        referenced anywhere once nav_dashboard/nav_my_calendar existed —
        dead duplicate vocabulary, not real backward compatibility."""
        assert not hasattr(STRINGS, "nav_home")
        assert not hasattr(STRINGS, "nav_calendar")

    def test_empty_state_titles_never_end_with_a_period(self) -> None:
        """Sprint 54: EmptyState titles read as short labels, never full
        sentences — only genuine instructional sentences with a verb
        (weekend_next_hint/search_empty_query/about_description) keep a
        trailing period."""
        for key in (
            "weekend_empty_title",
            "dashboard_weekend_championships_empty",
            "dashboard_next_race_empty",
            "calendar_season_explorer_empty",
            "calendar_summary_empty_selection",
            "search_no_results",
        ):
            value = getattr(STRINGS, key)
            assert not value.endswith("."), f"{key} still ends with a period: {value!r}"

    def test_about_version_carries_a_version_placeholder(self) -> None:
        """Sprint 54: about_version must be a format string, not a bare
        'Version Alpha' with no actual number — see views/about.py."""
        assert "{version}" in STRINGS.about_version


class TestPlural:
    def test_zero_returns_s(self) -> None:
        assert plural(0) == "s"

    def test_one_returns_empty(self) -> None:
        assert plural(1) == ""

    def test_two_returns_s(self) -> None:
        assert plural(2) == "s"

    def test_negative_returns_s(self) -> None:
        assert plural(-1) == "s"
