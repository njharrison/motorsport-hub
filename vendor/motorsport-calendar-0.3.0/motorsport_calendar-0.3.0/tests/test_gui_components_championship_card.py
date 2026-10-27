"""Tests for the ChampionshipCard component (Sprint 30).

The component is a pure ft.Control builder: no Flet runtime, no HTTP, no
domain models. These tests lock in exactly what the spec asked for: fixed
header order, aligned session grid, empty-by-default footer, and the
extension point for future actions.
"""

from __future__ import annotations

import flet as ft
import pytest

from motorsport_calendar.gui import championship_assets, theme
from motorsport_calendar.gui.components.championship_card import (
    ChampionshipCardData,
    SessionRow,
    build_championship_card,
)


def _sessions_column(card: ft.Container) -> ft.Column:
    """The card's header/body/footer sections are flat children of one
    Column — the sessions grid is the only *nested* Column among them."""
    header_column = card.content
    return next(c for c in header_column.controls if isinstance(c, ft.Column))


def _make_data(**overrides) -> ChampionshipCardData:
    defaults = {
        "championship_id": "formula1",
        "championship_name": "Formula 1",
        "event_name": "Belgian Grand Prix",
        "circuit_name": "Spa-Francorchamps",
        "country": "🇧🇪 Belgique",
        "sessions": (
            SessionRow("Essais Libres 1", "Vendredi 13:30"),
            SessionRow("Qualifications", "Samedi 16:00"),
            SessionRow("Course", "Dimanche 15:00"),
        ),
    }
    defaults.update(overrides)
    return ChampionshipCardData(**defaults)


class TestChampionshipCardData:
    def test_is_frozen(self) -> None:
        data = _make_data()
        with pytest.raises(AttributeError):
            data.championship_name = "Formula 2"  # type: ignore[misc]

    def test_session_row_is_frozen(self) -> None:
        row = SessionRow("Course", "Dimanche 15:00")
        with pytest.raises(AttributeError):
            row.label = "Autre"  # type: ignore[misc]

    def test_fields_round_trip(self) -> None:
        data = _make_data()
        assert data.championship_id == "formula1"
        assert data.championship_name == "Formula 1"
        assert data.event_name == "Belgian Grand Prix"
        assert data.circuit_name == "Spa-Francorchamps"
        assert data.country == "🇧🇪 Belgique"
        assert len(data.sessions) == 3


class TestChampionshipCardBuild:
    def test_returns_a_control(self) -> None:
        card = build_championship_card(_make_data())
        assert isinstance(card, ft.Control)

    def test_is_a_bordered_theme_card(self) -> None:
        """Must reuse theme.card() — no bespoke container/border of its own."""
        card = build_championship_card(_make_data())
        assert isinstance(card, ft.Container)
        assert card.border is not None

    def test_header_order_is_championship_then_event_then_circuit_then_country(self) -> None:
        card = build_championship_card(_make_data())
        column = card.content
        assert isinstance(column, ft.Column)
        texts = [c for c in column.controls if isinstance(c, ft.Text)]
        assert texts[0].value == "Formula 1"
        assert texts[1].value == "Belgian Grand Prix"
        assert texts[2].value == "Spa-Francorchamps"
        assert texts[3].value == "🇧🇪 Belgique"

    def test_championship_name_is_the_most_prominent_text(self) -> None:
        """Header hierarchy: championship name is bold and the largest text."""
        card = build_championship_card(_make_data())
        column = card.content
        championship_text = next(c for c in column.controls if isinstance(c, ft.Text))
        assert championship_text.weight == ft.FontWeight.BOLD
        assert championship_text.size == theme.FontSize.TITLE

    def test_there_is_a_divider_between_header_and_sessions(self) -> None:
        card = build_championship_card(_make_data())
        column = card.content
        assert any(isinstance(c, ft.Divider) for c in column.controls)


class TestOptionalMetadataLines:
    """Sprint 32: circuit_name/country are optional — deciding whether to
    hide them is the caller's job (gui/event_display.py); the component
    only has to skip rendering a None, never show it as blank/"Unknown"."""

    def test_circuit_line_omitted_when_none(self) -> None:
        card = build_championship_card(_make_data(circuit_name=None))
        texts = [c.value for c in card.content.controls if isinstance(c, ft.Text)]
        assert "Spa-Francorchamps" not in texts
        assert texts == ["Formula 1", "Belgian Grand Prix", "🇧🇪 Belgique"]

    def test_country_line_omitted_when_none(self) -> None:
        card = build_championship_card(_make_data(country=None))
        texts = [c.value for c in card.content.controls if isinstance(c, ft.Text)]
        assert "🇧🇪 Belgique" not in texts
        assert texts == ["Formula 1", "Belgian Grand Prix", "Spa-Francorchamps"]

    def test_both_omitted_leaves_only_championship_and_event(self) -> None:
        card = build_championship_card(_make_data(circuit_name=None, country=None))
        texts = [c.value for c in card.content.controls if isinstance(c, ft.Text)]
        assert texts == ["Formula 1", "Belgian Grand Prix"]

    def test_still_renders_and_has_a_divider_with_both_omitted(self) -> None:
        card = build_championship_card(_make_data(circuit_name=None, country=None))
        assert isinstance(card, ft.Control)
        assert any(isinstance(c, ft.Divider) for c in card.content.controls)


class TestSessionGrid:
    def test_one_row_per_session(self) -> None:
        card = build_championship_card(_make_data())
        assert len(_sessions_column(card).controls) == 3

    def test_session_order_is_preserved_not_resorted(self) -> None:
        """The component renders sessions in the order given — sorting is
        the caller's responsibility (e.g. upcoming_weekend.py already
        sorts chronologically before building the data)."""
        data = _make_data(
            sessions=(
                SessionRow("Course", "Dimanche 15:00"),
                SessionRow("Essais Libres 1", "Vendredi 13:30"),
            )
        )
        card = build_championship_card(data)
        labels = [row.controls[0].value for row in _sessions_column(card).controls]
        assert labels == ["Course", "Essais Libres 1"]

    def test_each_session_row_is_aligned_label_left_time_right(self) -> None:
        """ "Un vrai alignement" — label and time anchored to opposite ends
        of the row, regardless of label length."""
        card = build_championship_card(_make_data())
        for row in _sessions_column(card).controls:
            assert isinstance(row, ft.Row)
            assert row.alignment == ft.MainAxisAlignment.SPACE_BETWEEN
            label_text, time_text = row.controls
            assert isinstance(label_text, ft.Text)
            assert isinstance(time_text, ft.Text)

    def test_alignment_is_identical_regardless_of_label_length(self) -> None:
        """A short label and a long label must produce the same alignment
        strategy — nothing hardcodes a column width tied to text length."""
        short = _make_data(sessions=(SessionRow("FP1", "Vendredi 10:30"),))
        long = _make_data(sessions=(SessionRow("Qualifications Sprint", "Vendredi 10:30"),))
        short_row = _sessions_column(build_championship_card(short)).controls[0]
        long_row = _sessions_column(build_championship_card(long)).controls[0]
        assert short_row.alignment == long_row.alignment == ft.MainAxisAlignment.SPACE_BETWEEN

    def test_zero_sessions_does_not_crash(self) -> None:
        card = build_championship_card(_make_data(sessions=()))
        assert isinstance(card, ft.Control)


class TestFooterExtensionPoint:
    def test_no_footer_by_default(self) -> None:
        card = build_championship_card(_make_data())
        column = card.content
        assert not any(
            isinstance(c, ft.Text) and c.value and "⭐" in c.value for c in column.controls
        )

    def test_omitting_footer_renders_exactly_the_header_and_sessions_sections(self) -> None:
        """4 header texts + 1 divider + 1 sessions column = 6 sections,
        with no trailing divider/footer when footer=None."""
        card = build_championship_card(_make_data())
        assert len(card.content.controls) == 6

    def test_footer_control_is_appended_after_a_divider(self) -> None:
        footer = ft.Text("⭐ Favori")
        card = build_championship_card(_make_data(), footer=footer)
        column = card.content
        assert column.controls[-1] is footer
        assert isinstance(column.controls[-2], ft.Divider)
        # 6 sections without a footer + 1 extra divider + the footer itself
        assert len(column.controls) == 8

    def test_footer_accepts_any_control_the_component_does_not_interpret_it(self) -> None:
        """The component must not know what a favori/notification/export
        button looks like — it only places whatever control it is given."""
        footer = ft.Row([ft.IconButton(icon=ft.Icons.STAR_BORDER), ft.Text("Favori")])
        card = build_championship_card(_make_data(), footer=footer)
        assert card.content.controls[-1] is footer


class TestCircuitClickExtensionPoint:
    """Sprint 47: the circuit name becomes clickable only when a caller
    opts in via ``on_circuit_click`` — every other consumer keeps the
    exact same plain, non-interactive line as before this sprint."""

    def _circuit_control(self, card: ft.Container) -> ft.Control:
        column = card.content
        return next(
            c
            for c in column.controls
            if (isinstance(c, ft.Text) and c.value == "Spa-Francorchamps")
            or (
                isinstance(c, ft.Container)
                and isinstance(c.content, ft.Text)
                and c.content.value == "Spa-Francorchamps"
            )
        )

    def test_circuit_name_is_plain_text_by_default(self) -> None:
        card = build_championship_card(_make_data())
        control = self._circuit_control(card)
        assert isinstance(control, ft.Text)
        assert control.color == theme.Colors.TEXT_MUTED

    def test_circuit_name_becomes_a_clickable_container_when_wired(self) -> None:
        card = build_championship_card(_make_data(), on_circuit_click=lambda: None)
        control = self._circuit_control(card)
        assert isinstance(control, ft.Container)
        assert control.on_click is not None
        assert control.content.value == "Spa-Francorchamps"
        assert control.content.color == theme.Colors.PRIMARY

    def test_clicking_calls_the_handler_with_no_arguments(self) -> None:
        calls: list[None] = []
        card = build_championship_card(_make_data(), on_circuit_click=lambda: calls.append(None))
        control = self._circuit_control(card)
        control.on_click(None)
        assert calls == [None]

    def test_no_circuit_name_means_nothing_to_click_even_when_wired(self) -> None:
        """When circuit_name is hidden (redundant with the headline), there
        is no text to attach a click handler to — on_circuit_click is
        simply never invoked, not an error."""
        card = build_championship_card(_make_data(circuit_name=None), on_circuit_click=lambda: None)
        column = card.content
        assert not any(
            isinstance(c, ft.Container) and c.on_click is not None for c in column.controls
        )

    def test_omitting_on_circuit_click_does_not_change_the_section_count(self) -> None:
        card = build_championship_card(_make_data())
        assert len(card.content.controls) == 6


class TestReusabilityAcrossChampionships:
    """The whole point of extracting this component: any championship, any
    event shape, renders through the exact same builder."""

    @pytest.mark.parametrize(
        ("championship_name", "event_name"),
        [
            ("Formula 1", "Belgian Grand Prix"),
            ("Formula 2", "Belgian Grand Prix"),
            ("Formula 3", "Belgian Grand Prix"),
            ("FIA WEC", "24 Hours of Le Mans"),
            ("F1 Academy", "Belgian Grand Prix"),
        ],
    )
    def test_renders_for_every_current_championship(
        self, championship_name: str, event_name: str
    ) -> None:
        data = _make_data(championship_name=championship_name, event_name=event_name)
        card = build_championship_card(data)
        assert isinstance(card, ft.Control)
        texts = [c for c in card.content.controls if isinstance(c, ft.Text)]
        assert texts[0].value == championship_name
        assert texts[1].value == event_name

    def test_a_long_running_endurance_event_name_does_not_break_the_layout(self) -> None:
        """Sanity check for a very different event shape (WEC's "24 Hours
        of Le Mans" vs. a Grand Prix) — same component, no special-casing."""
        data = _make_data(
            championship_id="wec",
            championship_name="FIA WEC",
            event_name="24 Hours of Le Mans",
            circuit_name="Circuit des 24 Heures",
            country="🇫🇷 France",
            sessions=(SessionRow("Course", "Samedi 16:00"),),
        )
        card = build_championship_card(data)
        assert isinstance(card, ft.Control)


class TestChampionshipLogo:
    """Sprint 33: the logo, resolved through the ``championship_assets``
    registry, sits to the left of the championship name. No file is
    delivered in the real repo, so these tests monkeypatch the registry's
    asset directory to simulate a championship that does have one."""

    def test_no_logo_delivered_renders_a_bare_text_title_unchanged(self) -> None:
        """Default state today for every championship: exactly the
        pre-Sprint-33 layout, no Row wrapper, no reserved empty space."""
        card = build_championship_card(_make_data())
        title = card.content.controls[0]
        assert isinstance(title, ft.Text)
        assert title.value == "Formula 1"

    def test_unknown_championship_id_does_not_break_rendering(self) -> None:
        card = build_championship_card(_make_data(championship_id="nascar"))
        title = card.content.controls[0]
        assert isinstance(title, ft.Text)
        assert title.value == "Formula 1"

    def test_logo_delivered_renders_image_before_title_in_a_row(
        self, tmp_path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(championship_assets, "_ASSETS_DIR", tmp_path)
        (tmp_path / "formula1.png").touch()

        card = build_championship_card(_make_data(championship_id="formula1"))
        title_row = card.content.controls[0]

        assert isinstance(title_row, ft.Row)
        logo, title = title_row.controls
        assert isinstance(logo, ft.Image)
        assert logo.src == "championships/formula1.png"
        assert isinstance(title, ft.Text)
        assert title.value == "Formula 1"

    def test_logo_size_matches_design_system_icon_size(
        self, tmp_path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(championship_assets, "_ASSETS_DIR", tmp_path)
        (tmp_path / "formula1.png").touch()

        card = build_championship_card(_make_data(championship_id="formula1"))
        logo = card.content.controls[0].controls[0]

        assert logo.width == theme.IconSize.LG
        assert logo.height == theme.IconSize.LG

    def test_logo_delivered_does_not_change_the_rest_of_the_header_order(
        self, tmp_path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Adding the logo must not shift circuit/country/session sections
        — only the title's own control changes shape."""
        monkeypatch.setattr(championship_assets, "_ASSETS_DIR", tmp_path)
        (tmp_path / "formula1.png").touch()

        card = build_championship_card(_make_data(championship_id="formula1"))
        texts = [c.value for c in card.content.controls if isinstance(c, ft.Text)]
        assert texts == ["Belgian Grand Prix", "Spa-Francorchamps", "🇧🇪 Belgique"]
