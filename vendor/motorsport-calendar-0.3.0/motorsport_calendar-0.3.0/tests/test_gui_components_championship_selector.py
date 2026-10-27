"""Tests for gui.components.championship_selector (Sprint 43, extracted to
this shared module in Sprint 44) — single-level accordions (one per
category) containing selectable "buttons" (never checkboxes, never radio
buttons — multi-select stays possible). Shared by "Mon calendrier" and
"Mes favoris".
"""

from __future__ import annotations

import flet as ft

from motorsport_calendar.gui import theme
from motorsport_calendar.gui.components.championship_selector import (
    ChampionshipButtonData,
    ChampionshipCategoryData,
    _category_accordion,
    _championship_button,
    build_championship_selector,
)


def _texts(control: ft.Control) -> list[str]:
    found: list[str] = []
    if isinstance(control, ft.Text) and control.value:
        found.append(str(control.value))
    # "title" — ft.ExpansionTile keeps its title separate from "controls"
    # (its expandable body) and "content".
    for attr in ("controls", "content", "title"):
        child = getattr(control, attr, None)
        if isinstance(child, list):
            for c in child:
                found.extend(_texts(c))
        elif isinstance(child, ft.Control):
            found.extend(_texts(child))
    return found


def _button_data(**overrides):
    defaults = {
        "championship_id": "formula1",
        "display_name": "Formula 1",
        "selected": False,
    }
    defaults.update(overrides)
    return ChampionshipButtonData(**defaults)


def _category_data(**overrides):
    defaults = {
        "category_id": "formula",
        "label": "🏎  Formula",
        "expanded": False,
        "options": (_button_data(),),
    }
    defaults.update(overrides)
    return ChampionshipCategoryData(**defaults)


class TestChampionshipButton:
    def test_button_shows_display_name(self):
        button = _championship_button(_button_data(display_name="MotoGP"), lambda cid: None)
        assert "MotoGP" in _texts(button)

    def test_button_is_a_theme_card(self):
        """Reuses theme.card()'s existing selected-state style (anticipated
        since Sprint 26/30, unused until Sprint 43) — no new Design System
        token."""
        button = _championship_button(_button_data(), lambda cid: None)
        assert isinstance(button, ft.Container)
        assert button.border is not None

    def test_selected_button_uses_the_selected_card_style(self):
        selected = _championship_button(_button_data(selected=True), lambda cid: None)
        unselected = _championship_button(_button_data(selected=False), lambda cid: None)
        assert selected.border.top.color == theme.Colors.BORDER_ACTIVE
        assert unselected.border.top.color == theme.Colors.BORDER
        assert selected.bgcolor == theme.Colors.SURFACE
        assert unselected.bgcolor is None

    def test_clicking_a_button_calls_on_click_with_its_championship_id(self):
        clicked: list[str] = []
        button = _championship_button(_button_data(championship_id="motogp"), clicked.append)
        assert button.on_click is not None
        button.on_click(None)  # simulate a Flet click event
        assert clicked == ["motogp"]

    def test_no_radio_buttons_used_anywhere(self):
        """The brief explicitly forbids radio buttons — multi-select must
        stay possible."""
        button = _championship_button(_button_data(), lambda cid: None)
        assert not isinstance(button, ft.Radio)

    def test_multiple_selected_options_all_keep_their_selected_style(self):
        """Multi-select must stay possible — selecting one championship
        must not visually or behaviorally deselect another."""
        a = _championship_button(
            _button_data(championship_id="formula1", selected=True), lambda cid: None
        )
        b = _championship_button(
            _button_data(championship_id="motogp", selected=True), lambda cid: None
        )
        assert a.bgcolor is not None
        assert b.bgcolor is not None


class TestCategoryAccordion:
    def test_accordion_is_an_expansion_tile(self):
        accordion = _category_accordion(_category_data(), lambda cid: None, lambda c, e: None)
        assert isinstance(accordion, ft.ExpansionTile)

    def test_accordion_title_shows_category_label(self):
        accordion = _category_accordion(
            _category_data(label="🏁  Endurance"), lambda cid: None, lambda c, e: None
        )
        assert "🏁  Endurance" in _texts(accordion.title)

    def test_accordion_expanded_state_reflects_the_data(self):
        expanded = _category_accordion(
            _category_data(expanded=True), lambda cid: None, lambda c, e: None
        )
        collapsed = _category_accordion(
            _category_data(expanded=False), lambda cid: None, lambda c, e: None
        )
        assert expanded.expanded is True
        assert collapsed.expanded is False

    def test_accordion_contains_one_button_per_option(self):
        group = _category_data(
            options=(
                _button_data(championship_id="formula1", display_name="Formula 1"),
                _button_data(championship_id="formula2", display_name="Formula 2"),
            )
        )
        accordion = _category_accordion(group, lambda cid: None, lambda c, e: None)
        texts = _texts(accordion)
        assert "Formula 1" in texts
        assert "Formula 2" in texts

    def test_toggling_the_accordion_calls_on_category_toggle(self):
        toggled: list[tuple[str, bool]] = []
        accordion = _category_accordion(
            _category_data(category_id="endurance"),
            lambda cid: None,
            lambda cid, expanded: toggled.append((cid, expanded)),
        )
        fake_control = type("FakeControl", (), {"expanded": True})()
        fake_event = type("FakeEvent", (), {"control": fake_control})()
        accordion.on_change(fake_event)
        assert toggled == [("endurance", True)]

    def test_single_level_only_no_nested_accordions(self):
        """The brief explicitly asks for a single level of accordion."""
        accordion = _category_accordion(_category_data(), lambda cid: None, lambda c, e: None)

        def _count_expansion_tiles(control) -> int:
            count = 1 if isinstance(control, ft.ExpansionTile) else 0
            for attr in ("controls", "content"):
                child = getattr(control, attr, None)
                if isinstance(child, list):
                    count += sum(_count_expansion_tiles(c) for c in child)
                elif isinstance(child, ft.Control):
                    count += _count_expansion_tiles(child)
            return count

        assert _count_expansion_tiles(accordion) == 1


class TestBuildChampionshipSelector:
    def test_builds_one_accordion_per_group_in_order(self):
        groups = [
            _category_data(category_id="formula", label="🏎  Formula"),
            _category_data(category_id="endurance", label="🏁  Endurance"),
        ]
        section = build_championship_selector(groups, lambda cid: None, lambda c, e: None)
        texts = _texts(section)
        assert texts.index("🏎  Formula") < texts.index("🏁  Endurance")

    def test_empty_groups_does_not_crash(self):
        section = build_championship_selector([], lambda cid: None, lambda c, e: None)
        assert isinstance(section, ft.Control)

    def test_returns_a_control(self):
        section = build_championship_selector(
            [_category_data()], lambda cid: None, lambda c, e: None
        )
        assert isinstance(section, ft.Control)
