"""Tests for GUI display names module — no Flet dependency."""

from __future__ import annotations

from motorsport_calendar.gui.display_names import DEFAULT_SELECTED, get_display_name


class TestGetDisplayName:
    def test_formula1(self) -> None:
        assert get_display_name("formula1") == "Formula 1"

    def test_formula2(self) -> None:
        assert get_display_name("formula2") == "Formula 2"

    def test_formula3(self) -> None:
        assert get_display_name("formula3") == "Formula 3"

    def test_f1_academy(self) -> None:
        assert get_display_name("f1-academy") == "F1 Academy"

    def test_wec(self) -> None:
        assert get_display_name("wec") == "FIA WEC"

    def test_unknown_single_word(self) -> None:
        assert get_display_name("indy500") == "Indy500"

    def test_unknown_hyphenated(self) -> None:
        assert get_display_name("my-new-series") == "My New Series"

    def test_returns_string(self) -> None:
        assert isinstance(get_display_name("formula1"), str)

    def test_no_technical_ids_in_output(self) -> None:
        for cid in ["formula1", "formula2", "formula3", "f1-academy", "wec"]:
            name = get_display_name(cid)
            assert cid not in name, f"Technical ID '{cid}' leaked into display name '{name}'"


class TestDefaultSelected:
    def test_formula1_is_default(self) -> None:
        assert "formula1" in DEFAULT_SELECTED

    def test_is_list(self) -> None:
        assert isinstance(DEFAULT_SELECTED, list)

    def test_not_empty(self) -> None:
        assert len(DEFAULT_SELECTED) > 0

    def test_all_ids_are_strings(self) -> None:
        assert all(isinstance(cid, str) for cid in DEFAULT_SELECTED)
