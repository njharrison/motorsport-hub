"""Tests for the GUI design system (theme.py) — Sprint 26.

No Flet runtime required — controls are dataclasses/objects that
instantiate without a page.
"""

from __future__ import annotations

import re

import flet as ft
import pytest

from motorsport_calendar.gui import theme

_HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")


class TestColorPalettes:
    @pytest.mark.parametrize(
        "value",
        [
            theme.BAppsColors.BLUE,
            theme.BAppsColors.CYAN,
            theme.BAppsColors.BG_DARK,
            theme.BAppsColors.BG_LIGHT,
            theme.BAppsColors.TEXT_PRIMARY,
            theme.BAppsColors.TEXT_SECONDARY,
        ],
    )
    def test_bapps_colors_are_valid_hex(self, value: str) -> None:
        assert _HEX_RE.match(value)

    @pytest.mark.parametrize(
        "value",
        [
            theme.MotorsportColors.BLUE,
            theme.MotorsportColors.CYAN,
            theme.MotorsportColors.BLUE_DARK,
            theme.MotorsportColors.MIDNIGHT,
            theme.MotorsportColors.SURFACE_DARK,
            theme.MotorsportColors.SURFACE_LIGHT,
            theme.MotorsportColors.WHITE,
        ],
    )
    def test_motorsport_colors_are_valid_hex(self, value: str) -> None:
        assert _HEX_RE.match(value)

    def test_semantic_colors_map_to_product_palette(self) -> None:
        assert theme.Colors.PRIMARY == theme.MotorsportColors.BLUE
        assert theme.Colors.ACCENT == theme.MotorsportColors.CYAN
        assert theme.Colors.BACKGROUND == theme.MotorsportColors.MIDNIGHT
        assert theme.Colors.SURFACE == theme.MotorsportColors.SURFACE_DARK


class TestSpacingScale:
    def test_scale_is_strictly_increasing(self) -> None:
        values = [
            theme.Spacing.XXS,
            theme.Spacing.XS,
            theme.Spacing.SM,
            theme.Spacing.MD,
            theme.Spacing.LG,
            theme.Spacing.XL,
            theme.Spacing.XXL,
        ]
        assert values == sorted(values)
        assert len(set(values)) == len(values)


class TestRadiusScale:
    def test_scale_is_increasing(self) -> None:
        assert theme.Radius.SM < theme.Radius.MD < theme.Radius.LG < theme.Radius.PILL


class TestIconSizeScale:
    def test_scale_is_increasing(self) -> None:
        assert theme.IconSize.SM < theme.IconSize.MD < theme.IconSize.LG < theme.IconSize.XL


class TestPageLayout:
    def test_page_padding_returns_padding(self) -> None:
        padding = theme.page_padding()
        assert isinstance(padding, ft.Padding)

    def test_section_title_without_icon(self) -> None:
        control = theme.section_title("Préférences")
        assert isinstance(control, ft.Control)

    def test_section_title_with_icon(self) -> None:
        control = theme.section_title("Préférences", icon=ft.Icons.SETTINGS)
        assert isinstance(control, ft.Control)


class TestPageShell:
    """Sprint 27 — one shared grid for every top-level view."""

    def test_returns_container(self) -> None:
        shell = theme.page_shell(ft.Text("a"))
        assert isinstance(shell, ft.Container)

    def test_expand_true(self) -> None:
        shell = theme.page_shell(ft.Text("a"))
        assert shell.expand is True

    def test_centers_the_inner_column_horizontally(self) -> None:
        shell = theme.page_shell(ft.Text("a"))
        assert shell.alignment == ft.Alignment.TOP_CENTER

    def test_inner_container_is_capped_at_max_content_width(self) -> None:
        shell = theme.page_shell(ft.Text("a"))
        inner = shell.content
        assert isinstance(inner, ft.Container)
        assert inner.width == theme.MAX_CONTENT_WIDTH

    def test_max_content_width_is_within_the_900_to_1100_range(self) -> None:
        assert 900 <= theme.MAX_CONTENT_WIDTH <= 1100

    def test_content_column_is_left_aligned_never_centered(self) -> None:
        shell = theme.page_shell(ft.Text("a"))
        column = shell.content.content
        assert isinstance(column, ft.Column)
        # STRETCH fills the shell's width without centering any content —
        # centering is reserved for positioning the outer container only.
        assert column.horizontal_alignment == ft.CrossAxisAlignment.STRETCH

    def test_sections_are_forwarded_in_order(self) -> None:
        a, b, c = ft.Text("1"), ft.Divider(), ft.Text("2")
        shell = theme.page_shell(a, b, c)
        column = shell.content.content
        assert column.controls == [a, b, c]

    def test_outer_padding_matches_page_padding(self) -> None:
        shell = theme.page_shell(ft.Text("a"))
        assert shell.padding == theme.page_padding()


class TestButtonStyle:
    @pytest.mark.parametrize("variant", ["primary", "cta", "ghost"])
    def test_known_variants_return_button_style(self, variant: str) -> None:
        style = theme.button_style(variant)
        assert isinstance(style, ft.ButtonStyle)

    def test_unknown_variant_raises(self) -> None:
        with pytest.raises(KeyError):
            theme.button_style("does-not-exist")

    def test_cta_variant_uses_green(self) -> None:
        style = theme.button_style("cta")
        assert style.bgcolor == theme.Colors.CTA


class TestCard:
    def test_returns_container(self) -> None:
        c = theme.card(ft.Text("hello"))
        assert isinstance(c, ft.Container)

    def test_selected_uses_active_border(self) -> None:
        c = theme.card(ft.Text("hello"), selected=True)
        assert c.border.top.color == theme.Colors.BORDER_ACTIVE

    def test_unselected_uses_default_border(self) -> None:
        c = theme.card(ft.Text("hello"), selected=False)
        assert c.border.top.color == theme.Colors.BORDER

    def test_width_is_forwarded(self) -> None:
        c = theme.card(ft.Text("hello"), width=320)
        assert c.width == 320


class TestChip:
    def test_returns_control(self) -> None:
        assert isinstance(theme.chip("Disponible prochainement"), ft.Control)


class TestLogoPlaceholder:
    def test_icon_kind_is_square(self) -> None:
        c = theme.logo_placeholder("icon", size=48)
        assert c.width == 48
        assert c.height == 48

    def test_icon_default_size(self) -> None:
        c = theme.logo_placeholder("icon")
        assert c.width == theme.IconSize.XL

    def test_horizontal_kind_returns_control(self) -> None:
        c = theme.logo_placeholder("horizontal")
        assert isinstance(c, ft.Control)

    def test_has_placeholder_tooltip(self) -> None:
        c = theme.logo_placeholder("icon")
        assert "placeholder" in c.tooltip.lower() or "Placeholder" in c.tooltip
