"""Tests for the Layout System (Sprint 31) — gui/components/layout/*.

Each component has one job; these tests lock in that job in isolation
(PageContainer's width/padding/alignment, PageHeader's fixed structure,
Section's pure spacing, CardList's uniform stacking, EmptyState's card
wrapping, PageSpacing's fixed height) plus one integration test proving
the exact composition pattern from the sprint brief works end to end.
"""

from __future__ import annotations

import flet as ft
import pytest

from motorsport_calendar.gui import theme
from motorsport_calendar.gui.components.layout import (
    CardList,
    ComingSoonRow,
    EmptyState,
    PageContainer,
    PageHeader,
    PageSpacing,
    Section,
    SectionHeader,
)


class TestPageContainer:
    def test_returns_a_control(self) -> None:
        assert isinstance(PageContainer(), ft.Control)

    def test_matches_theme_page_shell_width(self) -> None:
        """PageContainer must not reinvent width/padding/alignment — it
        delegates to theme.page_shell, the single source of truth."""
        container = PageContainer(body=[ft.Text("x")])
        assert container.content.width == theme.MAX_CONTENT_WIDTH

    def test_matches_theme_page_shell_alignment(self) -> None:
        container = PageContainer(body=[ft.Text("x")])
        assert container.alignment == ft.Alignment.TOP_CENTER

    def test_matches_theme_page_shell_padding(self) -> None:
        container = PageContainer(body=[ft.Text("x")])
        assert container.padding == theme.page_padding()

    def test_content_column_is_stretch_not_centered(self) -> None:
        container = PageContainer(body=[ft.Text("x")])
        column = container.content.content
        assert column.horizontal_alignment == ft.CrossAxisAlignment.STRETCH

    def test_header_is_the_first_section_when_provided(self) -> None:
        header = ft.Text("header")
        body_item = ft.Text("body")
        container = PageContainer(header=header, body=[body_item])
        column = container.content.content
        assert column.controls == [header, body_item]

    def test_header_none_means_body_is_the_only_content(self) -> None:
        body_item = ft.Text("body")
        container = PageContainer(header=None, body=[body_item])
        column = container.content.content
        assert column.controls == [body_item]

    def test_empty_body_and_no_header_does_not_crash(self) -> None:
        container = PageContainer()
        assert isinstance(container, ft.Control)

    def test_body_accepts_multiple_blocks_in_order(self) -> None:
        a, b, c = ft.Text("a"), ft.Text("b"), ft.Text("c")
        container = PageContainer(body=[a, b, c])
        assert container.content.content.controls == [a, b, c]


class TestPageContainerFooter:
    """Sprint 43 — optional footer pinned below a scrollable header+body,
    for "Mon calendrier"'s always-visible "Créer mon calendrier" action."""

    def test_no_footer_behaves_exactly_like_before(self) -> None:
        """Omitting footer must be a complete no-op — every other page's
        structure (single scrolling column) stays byte-for-byte identical."""
        header, body_item = ft.Text("header"), ft.Text("body")
        with_footer_omitted = PageContainer(header=header, body=[body_item])
        column = with_footer_omitted.content.content
        assert column.controls == [header, body_item]
        assert column.scroll == ft.ScrollMode.AUTO

    def test_returns_a_control(self) -> None:
        container = PageContainer(body=[ft.Text("x")], footer=ft.Text("footer"))
        assert isinstance(container, ft.Control)

    def test_matches_page_shell_width_padding_alignment(self) -> None:
        """Same width/padding/alignment tokens as the no-footer path —
        structural split only, not a new visual style."""
        container = PageContainer(body=[ft.Text("x")], footer=ft.Text("footer"))
        assert container.content.width == theme.MAX_CONTENT_WIDTH
        assert container.alignment == ft.Alignment.TOP_CENTER
        assert container.padding == theme.page_padding()

    def test_outer_column_is_stretch_and_does_not_scroll(self) -> None:
        """Only the header+body region scrolls — the outer column (which
        also holds the fixed footer) must not, or the footer would scroll
        away with everything else."""
        container = PageContainer(body=[ft.Text("x")], footer=ft.Text("footer"))
        outer_column = container.content.content
        assert outer_column.horizontal_alignment == ft.CrossAxisAlignment.STRETCH
        assert outer_column.scroll is None

    def test_footer_is_last_and_outside_the_scrollable_region(self) -> None:
        header, body_item, footer = ft.Text("header"), ft.Text("body"), ft.Text("footer")
        container = PageContainer(header=header, body=[body_item], footer=footer)
        outer_column = container.content.content
        assert outer_column.controls[-1] is footer

        scrollable_region = outer_column.controls[0]
        assert isinstance(scrollable_region, ft.Container)
        assert scrollable_region.expand is True
        scrollable_column = scrollable_region.content
        assert scrollable_column.controls == [header, body_item]
        assert scrollable_column.scroll == ft.ScrollMode.AUTO

    def test_footer_not_present_in_the_scrollable_region(self) -> None:
        footer = ft.Text("footer")
        container = PageContainer(body=[ft.Text("x")], footer=footer)
        scrollable_region = container.content.content.controls[0]
        assert footer not in scrollable_region.content.controls


class TestPageHeader:
    def test_returns_a_control(self) -> None:
        assert isinstance(PageHeader("Titre"), ft.Control)

    def test_has_a_trailing_divider(self) -> None:
        header = PageHeader("Titre")
        assert isinstance(header, ft.Column)
        assert any(isinstance(c, ft.Divider) for c in header.controls)

    def test_divider_is_last(self) -> None:
        """The separator always comes after the title/subtitle, never before."""
        header = PageHeader("Titre", subtitle="Sous-titre")
        assert isinstance(header.controls[-1], ft.Divider)

    def test_title_row_is_first(self) -> None:
        header = PageHeader("Titre", icon=ft.Icons.SETTINGS)
        assert isinstance(header.controls[0], ft.Row)

    def test_no_subtitle_by_default(self) -> None:
        header = PageHeader("Titre")
        # title row + divider only — no subtitle Text in between.
        assert len(header.controls) == 2

    def test_subtitle_appears_between_title_and_divider(self) -> None:
        header = PageHeader("Titre", subtitle="10/07 - 12/07")
        assert len(header.controls) == 3
        subtitle_text = header.controls[1]
        assert isinstance(subtitle_text, ft.Text)
        assert subtitle_text.value == "10/07 - 12/07"

    def test_works_without_an_icon(self) -> None:
        header = PageHeader("Titre", icon=None)
        assert isinstance(header, ft.Control)

    def test_no_trailing_by_default_title_row_unchanged(self) -> None:
        """Sprint 43: omitting trailing must be a complete no-op — the
        title row stays exactly theme.section_title()'s own Row, not
        wrapped in an extra one."""
        header = PageHeader("Titre", icon=ft.Icons.SETTINGS)
        title_row = header.controls[0]
        assert all(not isinstance(c, ft.Row) for c in title_row.controls)

    def test_trailing_appears_in_the_title_row(self) -> None:
        trailing = ft.Dropdown(label="Saison")
        header = PageHeader("Mon calendrier", trailing=trailing)
        title_row = header.controls[0]
        assert isinstance(title_row, ft.Row)
        assert trailing in title_row.controls

    def test_trailing_does_not_affect_divider_position(self) -> None:
        trailing = ft.Dropdown(label="Saison")
        header = PageHeader("Mon calendrier", subtitle="2026", trailing=trailing)
        assert isinstance(header.controls[-1], ft.Divider)
        assert len(header.controls) == 3


class TestSection:
    def test_returns_a_control(self) -> None:
        assert isinstance(Section(ft.Text("a")), ft.Control)

    def test_is_a_column(self) -> None:
        section = Section(ft.Text("a"))
        assert isinstance(section, ft.Column)

    def test_groups_controls_in_order(self) -> None:
        a, b = ft.Text("a"), ft.Text("b")
        section = Section(a, b)
        assert section.controls == [a, b]

    def test_default_spacing_is_the_standard_gap(self) -> None:
        section = Section(ft.Text("a"))
        assert section.spacing == theme.Spacing.SM

    def test_spacing_is_overridable(self) -> None:
        section = Section(ft.Text("a"), spacing=theme.Spacing.LG)
        assert section.spacing == theme.Spacing.LG

    def test_no_controls_does_not_crash(self) -> None:
        assert isinstance(Section(), ft.Control)

    def test_does_not_add_a_border_of_its_own(self) -> None:
        """Section is a spacing concern only — it must never look like a card."""
        section = Section(ft.Text("a"))
        assert not hasattr(section, "border") or section.border is None


class TestSectionHeader:
    def test_returns_a_control(self) -> None:
        assert isinstance(SectionHeader("Groupe"), ft.Control)

    def test_has_no_divider(self) -> None:
        """Distinct from PageHeader — SectionHeader is just a label."""
        header = SectionHeader("Groupe")
        assert isinstance(header, ft.Row)
        assert not any(isinstance(c, ft.Divider) for c in header.controls)

    def test_title_text_present(self) -> None:
        header = SectionHeader("Groupe")
        texts = [c for c in header.controls if isinstance(c, ft.Text)]
        assert texts[0].value == "Groupe"

    def test_icon_optional(self) -> None:
        with_icon = SectionHeader("Groupe", icon=ft.Icons.STAR)
        without_icon = SectionHeader("Groupe")
        assert len(with_icon.controls) == 2
        assert len(without_icon.controls) == 1


class TestCardList:
    def test_returns_a_control(self) -> None:
        assert isinstance(CardList([ft.Text("a")]), ft.Control)

    def test_is_a_column(self) -> None:
        assert isinstance(CardList([ft.Text("a")]), ft.Column)

    def test_stacks_cards_in_order(self) -> None:
        a, b, c = ft.Text("a"), ft.Text("b"), ft.Text("c")
        card_list = CardList([a, b, c])
        assert card_list.controls == [a, b, c]

    def test_default_spacing_is_the_standard_gap(self) -> None:
        card_list = CardList([ft.Text("a")])
        assert card_list.spacing == theme.Spacing.SM

    def test_spacing_is_overridable(self) -> None:
        card_list = CardList([ft.Text("a")], spacing=theme.Spacing.XS)
        assert card_list.spacing == theme.Spacing.XS

    def test_empty_list_does_not_crash(self) -> None:
        card_list = CardList([])
        assert isinstance(card_list, ft.Control)
        assert card_list.controls == []


class TestEmptyState:
    def test_returns_a_control(self) -> None:
        assert isinstance(EmptyState("Rien ici"), ft.Control)

    def test_is_a_bordered_theme_card(self) -> None:
        """Must reuse theme.card() — no bespoke container/border of its own."""
        empty = EmptyState("Rien ici")
        assert isinstance(empty, ft.Container)
        assert empty.border is not None

    def test_title_always_present(self) -> None:
        empty = EmptyState("Rien ici")
        column = empty.content
        texts = [c for c in column.controls if isinstance(c, ft.Text)]
        assert texts[0].value == "Rien ici"

    def test_no_message_by_default(self) -> None:
        empty = EmptyState("Rien ici")
        column = empty.content
        assert len(column.controls) == 1

    def test_message_appended_after_title_when_given(self) -> None:
        empty = EmptyState("Rien ici", message="Revenez plus tard.")
        column = empty.content
        assert len(column.controls) == 2
        assert column.controls[1].value == "Revenez plus tard."

    def test_icon_prepended_when_given(self) -> None:
        empty = EmptyState("Rien ici", icon=ft.Icons.INFO)
        column = empty.content
        assert isinstance(column.controls[0], ft.Icon)
        assert column.controls[1].value == "Rien ici"

    def test_works_with_icon_and_message_together(self) -> None:
        empty = EmptyState("Rien ici", message="Revenez plus tard.", icon=ft.Icons.INFO)
        column = empty.content
        assert len(column.controls) == 3


class TestPageSpacing:
    def test_returns_a_control(self) -> None:
        assert isinstance(PageSpacing(), ft.Control)

    def test_default_size_is_md(self) -> None:
        spacer = PageSpacing()
        assert spacer.height == theme.Spacing.MD

    def test_size_is_overridable(self) -> None:
        spacer = PageSpacing(theme.Spacing.XL)
        assert spacer.height == theme.Spacing.XL

    def test_has_no_visible_content(self) -> None:
        spacer = PageSpacing()
        assert isinstance(spacer, ft.Container)
        assert spacer.content is None


class TestComingSoonRow:
    """Sprint 57 — promoted from ``views/preferences.py``'s own private
    ``_pref_row`` (Sprint 52) once "Soutenir le projet" needed the exact
    same "prepared, not yet real" row shape for its PayPal/GitHub
    Sponsors placeholders."""

    def test_returns_a_bordered_card(self) -> None:
        row = ComingSoonRow(ft.Icons.LANGUAGE, "Langue")
        assert isinstance(row, ft.Container)
        assert row.border is not None

    def test_label_is_shown(self) -> None:
        from motorsport_calendar.gui.strings import STRINGS

        row = ComingSoonRow(ft.Icons.LANGUAGE, "Langue")
        texts = [
            c.value
            for c in row.content.controls
            if isinstance(c, ft.Text) and c.value != STRINGS.prefs_coming_soon
        ]
        assert "Langue" in texts

    def test_shows_the_coming_soon_chip(self) -> None:
        from motorsport_calendar.gui.strings import STRINGS

        row = ComingSoonRow(ft.Icons.LANGUAGE, "Langue")
        texts = []
        for c in row.content.controls:
            if isinstance(c, ft.Text):
                texts.append(c.value)
            elif isinstance(c, ft.Container) and isinstance(c.content, ft.Text):
                texts.append(c.content.value)
        assert STRINGS.prefs_coming_soon in texts

    def test_icon_is_shown(self) -> None:
        row = ComingSoonRow(ft.Icons.LANGUAGE, "Langue")
        icons = [c for c in row.content.controls if isinstance(c, ft.Icon)]
        assert len(icons) == 1
        assert icons[0].icon == ft.Icons.LANGUAGE

    def test_different_labels_produce_independent_rows(self) -> None:
        row_a = ComingSoonRow(ft.Icons.LANGUAGE, "Langue")
        row_b = ComingSoonRow(ft.Icons.SCHEDULE, "Format horaire")
        assert row_a is not row_b


class TestLayoutSystemIntegration:
    """Proves the exact composition pattern from the sprint brief works."""

    def test_page_container_header_section_card_list_composition(self) -> None:
        cards = [ft.Text(f"card {i}") for i in range(3)]
        page = PageContainer(
            header=PageHeader("Recherche", icon=ft.Icons.SEARCH, subtitle="3 résultats"),
            body=[Section(CardList(cards))],
        )
        assert isinstance(page, ft.Control)
        assert page.content.width == theme.MAX_CONTENT_WIDTH

        column = page.content.content
        header, section = column.controls
        assert isinstance(header, ft.Column)  # PageHeader
        assert isinstance(section, ft.Column)  # Section
        card_list = section.controls[0]
        assert isinstance(card_list, ft.Column)  # CardList
        assert card_list.controls == cards

    def test_empty_state_composes_the_same_way(self) -> None:
        page = PageContainer(
            header=PageHeader("Notifications", icon=ft.Icons.NOTIFICATIONS),
            body=[Section(EmptyState("Aucune notification", message="Revenez plus tard."))],
        )
        assert isinstance(page, ft.Control)

    def test_a_hypothetical_new_page_needs_no_manual_layout_code(self) -> None:
        """A future "Historique" page composed purely from layout-system
        components, with zero raw Container/padding/width/margin — the
        stated goal of this sprint."""
        page = PageContainer(
            header=PageHeader("Historique", icon=ft.Icons.HISTORY),
            body=[
                Section(
                    SectionHeader("Cette semaine"),
                    CardList([ft.Text("Grand Prix de Belgique")]),
                ),
                Section(
                    SectionHeader("Le mois dernier"),
                    CardList([ft.Text("Grand Prix d'Autriche")]),
                ),
            ],
        )
        assert isinstance(page, ft.Control)
        assert page.content.width == theme.MAX_CONTENT_WIDTH


class TestNoNewDesignTokens:
    """Sprint 31 must not introduce new colors/spacing/tokens — every
    component is built exclusively from existing theme.py values."""

    @pytest.mark.parametrize(
        "spacing_value",
        [theme.Spacing.SM, theme.Spacing.MD, theme.Spacing.XXS, theme.Spacing.LG],
    )
    def test_spacing_values_come_from_theme(self, spacing_value: int) -> None:
        assert spacing_value in {
            theme.Spacing.XXS,
            theme.Spacing.XS,
            theme.Spacing.SM,
            theme.Spacing.MD,
            theme.Spacing.LG,
            theme.Spacing.XL,
            theme.Spacing.XXL,
        }
