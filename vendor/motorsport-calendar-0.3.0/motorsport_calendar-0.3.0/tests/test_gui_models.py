"""Tests for GUI state models — no Flet dependency."""

from __future__ import annotations

from datetime import date

from motorsport_calendar.gui.models import (
    DEFAULT_YEAR_SENTINEL,
    GenerateState,
    resolve_default_year,
)


class TestGenerateStateDefaults:
    def test_default_year_is_current(self) -> None:
        assert GenerateState().year == date.today().year

    def test_default_selection_is_empty(self) -> None:
        assert GenerateState().selected_championships == []

    def test_default_output_path_is_empty(self) -> None:
        assert GenerateState().output_path == ""

    def test_default_is_not_generating(self) -> None:
        assert GenerateState().is_generating is False

    def test_two_instances_share_no_list(self) -> None:
        a, b = GenerateState(), GenerateState()
        a.selected_championships.append("formula1")
        assert b.selected_championships == []


class TestGenerateStateIsReady:
    def test_not_ready_with_no_championships(self) -> None:
        state = GenerateState(output_path="/tmp/out.ics")
        assert not state.is_ready()

    def test_not_ready_with_no_output_path(self) -> None:
        state = GenerateState(selected_championships=["formula1"])
        assert not state.is_ready()

    def test_not_ready_when_generating(self) -> None:
        state = GenerateState(
            selected_championships=["formula1"],
            output_path="/tmp/out.ics",
            is_generating=True,
        )
        assert not state.is_ready()

    def test_ready_when_all_conditions_met(self) -> None:
        state = GenerateState(
            selected_championships=["formula1"],
            output_path="/tmp/out.ics",
        )
        assert state.is_ready()

    def test_ready_with_multiple_championships(self) -> None:
        state = GenerateState(
            selected_championships=["formula1", "formula2", "formula3"],
            output_path="/tmp/calendrier.ics",
        )
        assert state.is_ready()

    def test_becomes_not_ready_when_generating_starts(self) -> None:
        state = GenerateState(
            selected_championships=["formula1"],
            output_path="/tmp/out.ics",
        )
        assert state.is_ready()
        state.is_generating = True
        assert not state.is_ready()

    def test_becomes_ready_again_after_generation_ends(self) -> None:
        state = GenerateState(
            selected_championships=["formula1"],
            output_path="/tmp/out.ics",
            is_generating=True,
        )
        assert not state.is_ready()
        state.is_generating = False
        assert state.is_ready()

    def test_no_wizard_step_machinery_remains(self) -> None:
        """Sprint 43: the 4-step wizard was replaced by a single
        reorganized page — current_step/STEP_COUNT/step_valid/can_advance/
        can_go_back no longer exist."""
        state = GenerateState()
        for attr in (
            "current_step",
            "STEP_COUNT",
            "step_valid",
            "can_advance",
            "can_go_back",
        ):
            assert not hasattr(state, attr), f"stale wizard attribute still present: {attr}"


class TestResolveDefaultYear:
    """Sprint 52 — "année par défaut" preference decoding."""

    def test_sentinel_resolves_to_current_year(self) -> None:
        assert resolve_default_year(DEFAULT_YEAR_SENTINEL) == date.today().year

    def test_sentinel_resolves_to_explicit_current_year(self) -> None:
        assert resolve_default_year(DEFAULT_YEAR_SENTINEL, current_year=2030) == 2030

    def test_literal_year_string_is_parsed(self) -> None:
        assert resolve_default_year("2027") == 2027

    def test_literal_year_ignores_current_year_override(self) -> None:
        assert resolve_default_year("2027", current_year=2030) == 2027

    def test_corrupted_value_falls_back_to_current_year(self) -> None:
        """A hand-edited or corrupted preferences file must never crash
        "Mon calendrier"'s startup — falls back to today's year instead."""
        assert resolve_default_year("not-a-year") == date.today().year

    def test_corrupted_value_falls_back_to_explicit_current_year(self) -> None:
        assert resolve_default_year("not-a-year", current_year=2030) == 2030

    def test_empty_string_falls_back_to_current_year(self) -> None:
        assert resolve_default_year("") == date.today().year
