"""Smoke tests for GUI view builders.

Verify that each view module is importable and its builder returns a Flet control.
No Flet runtime required — controls are dataclasses and instantiate without a page.
"""

from __future__ import annotations

import flet as ft

from motorsport_calendar.gui import theme
from motorsport_calendar.gui.models import PreferencesModel
from motorsport_calendar.gui.search_service import SearchResults


def _bordered_cards(control: ft.Control) -> list[ft.Container]:
    """Recursively collect every bordered Container under *control* — used
    to assert "N cards present" without hardcoding exact nesting depth
    (Section/CardList/PageHeader each add their own wrapping Column)."""
    found: list[ft.Container] = []
    if isinstance(control, ft.Container) and control.border is not None:
        found.append(control)
    for attr in ("controls", "content"):
        child = getattr(control, attr, None)
        if isinstance(child, list):
            for c in child:
                found.extend(_bordered_cards(c))
        elif isinstance(child, ft.Control):
            found.extend(_bordered_cards(child))
    return found


def _flatten_controls(control: ft.Control) -> list[ft.Control]:
    """Recursively collect every control under (and including) *control*
    — used to assert a specific pre-built control instance (e.g. a Switch
    with its handler already wired) is actually rendered, not rebuilt."""
    found: list[ft.Control] = [control]
    for attr in ("controls", "content"):
        child = getattr(control, attr, None)
        if isinstance(child, list):
            for c in child:
                found.extend(_flatten_controls(c))
        elif isinstance(child, ft.Control):
            found.extend(_flatten_controls(child))
    return found


def _collect_all_text(control: ft.Control) -> list[str]:
    """Recursively collect every ``ft.Text``'s string value under *control*."""
    acc: list[str] = []
    if isinstance(control, ft.Text) and isinstance(control.value, str):
        acc.append(control.value)
    for attr in ("controls", "content"):
        child = getattr(control, attr, None)
        if isinstance(child, list):
            for c in child:
                acc.extend(_collect_all_text(c))
        elif isinstance(child, ft.Control):
            acc.extend(_collect_all_text(child))
    return acc


def _make_dashboard_data(*, found=True, cards=(), next_race=None, **overrides):
    """Shared by every Dashboard-related test class below (Sprint 53:
    promoted from a ``TestDashboardView``-private method once the new
    "Nouveautés"/"Accès rapides"/"État" test classes needed the exact
    same builder — one implementation, not four near-identical copies)."""
    from datetime import date

    from motorsport_calendar.gui.dashboard import DashboardData
    from motorsport_calendar.gui.upcoming_weekend import WeekendResult

    weekend = WeekendResult(
        found=found,
        friday=date(2026, 7, 10) if found else None,
        sunday=date(2026, 7, 12) if found else None,
        cards=cards,
    )
    defaults = {
        "total_championships": 17,
        "total_events_season": 150,
        "total_sessions_season": 700,
        "weekend": weekend,
        "next_race": next_race,
    }
    defaults.update(overrides)
    return DashboardData(**defaults)


class TestDashboardView:
    def _make_data(self, *, found=True, cards=(), next_race=None, **overrides):
        return _make_dashboard_data(found=found, cards=cards, next_race=next_race, **overrides)

    def test_import(self):
        from motorsport_calendar.gui.views import dashboard  # noqa: F401

    def test_build_returns_control(self):
        from motorsport_calendar.gui.views.dashboard import build_dashboard_view

        view = build_dashboard_view()
        assert isinstance(view, ft.Control)

    def test_build_is_container(self):
        from motorsport_calendar.gui.views.dashboard import build_dashboard_view

        view = build_dashboard_view()
        assert isinstance(view, ft.Container)

    def test_expand_true(self):
        from motorsport_calendar.gui.views.dashboard import build_dashboard_view

        view = build_dashboard_view()
        assert view.expand is True

    def test_uses_shared_page_shell(self):
        from motorsport_calendar.gui.views.dashboard import build_dashboard_view

        view = build_dashboard_view()
        assert view.content.width == theme.MAX_CONTENT_WIDTH

    def test_loading_state_is_card_wrapped(self):
        from motorsport_calendar.gui.views.dashboard import build_dashboard_view

        view = build_dashboard_view(None)
        assert len(_bordered_cards(view)) == 1

    def test_page_header_is_present(self):
        from motorsport_calendar.gui.views.dashboard import build_dashboard_view

        view = build_dashboard_view()
        column = view.content.content
        assert len(column.controls) == 2  # PageHeader, then the body

    def test_header_icon_matches_the_nav_rails_filled_dashboard_glyph(self):
        """Sprint 54: the header used to show the outlined
        SPACE_DASHBOARD_OUTLINED glyph — every other page's header icon
        matches its nav rail's filled/selected variant (SPACE_DASHBOARD
        here), this page now does too."""
        from motorsport_calendar.gui.views.dashboard import build_dashboard_view

        view = build_dashboard_view()
        column = view.content.content
        header = column.controls[0]
        icon_row = header.controls[0]
        icon = next(c for c in icon_row.controls if isinstance(c, ft.Icon))
        assert icon.icon == ft.Icons.SPACE_DASHBOARD

    def test_loaded_state_shows_four_stat_cards_when_weekend_and_race_empty(self):
        """4 stat cards + 2 EmptyState cards (weekend champs, next race) +
        4 quick-access cards + 4 status stat cards (Sprint 53, always
        present regardless of weekend/next-race data) = 14. "Nouveautés"
        contributes 0 here — no ``update`` set on the fixture data, so the
        brief's "aucune mise à jour -> ne rien afficher" omits it
        entirely (see TestDashboardViewNews below)."""
        from motorsport_calendar.gui.views.dashboard import build_dashboard_view

        data = self._make_data(found=False, cards=(), next_race=None)
        view = build_dashboard_view(data)
        assert len(_bordered_cards(view)) == 14

    def test_loaded_state_with_weekend_championships_renders_chips_not_empty_state(self):
        from motorsport_calendar.gui.components.championship_card import (
            ChampionshipCardData,
            SessionRow,
        )
        from motorsport_calendar.gui.views.dashboard import build_dashboard_view

        card = ChampionshipCardData(
            championship_id="formula1",
            championship_name="Formula 1",
            event_name="Grand Prix du Japon",
            circuit_name="Suzuka",
            country="🇯🇵 Japon",
            sessions=(SessionRow("Course", "Dimanche 14:00"),),
        )
        data = self._make_data(found=True, cards=(card,), next_race=None)
        view = build_dashboard_view(data)
        # 4 stat cards + 1 chip (theme.chip is itself bordered) + 1 EmptyState
        # (next race only, no weekend EmptyState) + 4 quick-access + 4 status
        # (Sprint 53) = 14
        assert len(_bordered_cards(view)) == 14

    def test_loaded_state_with_next_race_renders_card_not_empty_state(self):
        from motorsport_calendar.gui.dashboard import NextRaceStart
        from motorsport_calendar.gui.views.dashboard import build_dashboard_view

        next_race = NextRaceStart(championship_name="Formula 1", display="Dimanche 12/07 14:00")
        data = self._make_data(found=False, cards=(), next_race=next_race)
        view = build_dashboard_view(data)
        # 4 stat cards + 1 EmptyState (weekend champs only) + 1 next-race card
        # + 4 quick-access + 4 status (Sprint 53) = 14
        assert len(_bordered_cards(view)) == 14

    def test_loaded_state_fully_populated_does_not_crash(self):
        from motorsport_calendar.gui.components.championship_card import (
            ChampionshipCardData,
            SessionRow,
        )
        from motorsport_calendar.gui.dashboard import NextRaceStart
        from motorsport_calendar.gui.views.dashboard import build_dashboard_view

        card = ChampionshipCardData(
            championship_id="formula1",
            championship_name="Formula 1",
            event_name="Grand Prix du Japon",
            circuit_name="Suzuka",
            country="🇯🇵 Japon",
            sessions=(SessionRow("Course", "Dimanche 14:00"),),
        )
        next_race = NextRaceStart(championship_name="Formula 1", display="Dimanche 12/07 14:00")
        data = self._make_data(found=True, cards=(card,), next_race=next_race)
        view = build_dashboard_view(data)
        assert isinstance(view, ft.Control)


class TestDashboardViewNews:
    """Sprint 53 — "Nouveautés" section: brief's two named scenarios,
    "Dashboard sans nouveauté" / "Dashboard avec nouveauté"."""

    def _update(self, *, available: bool, manifest=None):
        from motorsport_calendar.gui.update_service import UpdateCheckResult

        return UpdateCheckResult(
            update_available=available, current_version="0.2.0", manifest=manifest
        )

    def _manifest(self, **overrides):
        from motorsport_calendar.gui.update_service import UpdateManifest

        defaults = {
            "version": "0.3.0",
            "release_date": "2026-07-13",
            "title": "Motorsport Calendar 0.3.0",
            "summary": "Nouvelles fonctionnalités et correctifs.",
            "url": "https://example.test/releases/0.3.0",
        }
        defaults.update(overrides)
        return UpdateManifest(**defaults)

    def test_no_update_omits_the_section_entirely(self):
        """Brief, verbatim: "aucune mise à jour -> ne rien afficher" — not
        even a header, unlike every other Dashboard section."""
        from motorsport_calendar.gui.strings import STRINGS
        from motorsport_calendar.gui.views.dashboard import build_dashboard_view

        data = _make_dashboard_data(update=None)
        view = build_dashboard_view(data)
        texts = _collect_all_text(view)
        assert STRINGS.dashboard_section_news not in texts

    def test_update_available_false_omits_the_section(self):
        from motorsport_calendar.gui.strings import STRINGS
        from motorsport_calendar.gui.views.dashboard import build_dashboard_view

        data = _make_dashboard_data(update=self._update(available=False))
        view = build_dashboard_view(data)
        texts = _collect_all_text(view)
        assert STRINGS.dashboard_section_news not in texts

    def test_update_available_but_no_manifest_omits_the_section(self):
        """Defensive: update_available=True with manifest=None shouldn't
        happen in practice (UpdateService always pairs them), but the view
        must not crash or render a broken card if it ever does."""
        from motorsport_calendar.gui.strings import STRINGS
        from motorsport_calendar.gui.views.dashboard import build_dashboard_view

        data = _make_dashboard_data(update=self._update(available=True, manifest=None))
        view = build_dashboard_view(data)
        texts = _collect_all_text(view)
        assert STRINGS.dashboard_section_news not in texts

    def test_update_available_shows_the_section(self):
        from motorsport_calendar.gui.strings import STRINGS
        from motorsport_calendar.gui.views.dashboard import build_dashboard_view

        data = _make_dashboard_data(update=self._update(available=True, manifest=self._manifest()))
        view = build_dashboard_view(data)
        texts = _collect_all_text(view)
        assert STRINGS.dashboard_section_news in texts

    def test_new_version_and_summary_are_shown(self):
        from motorsport_calendar.gui.views.dashboard import build_dashboard_view

        manifest = self._manifest(version="1.0.0", summary="Résumé distinctif.")
        data = _make_dashboard_data(update=self._update(available=True, manifest=manifest))
        view = build_dashboard_view(data)
        texts = _collect_all_text(view)
        assert "1.0.0" in texts
        assert "Résumé distinctif." in texts

    def test_view_release_button_is_present_and_labeled(self):
        """``ft.Button``'s ``content`` here is a plain string (not a nested
        ``ft.Text``), so it's invisible to ``_collect_all_text`` — check the
        button control itself, like the handler-identity test below does."""
        from motorsport_calendar.gui.strings import STRINGS
        from motorsport_calendar.gui.views.dashboard import build_dashboard_view

        data = _make_dashboard_data(update=self._update(available=True, manifest=self._manifest()))
        view = build_dashboard_view(data)
        buttons = [c for c in _flatten_controls(view) if isinstance(c, ft.Button)]
        assert any(b.content == STRINGS.update_view_btn for b in buttons)

    def test_view_release_button_uses_the_exact_handler_it_was_given(self):
        """Sprint 51's button behaviour must be reused, never duplicated —
        proven by checking the exact callable made it into the tree, not a
        second, view-local implementation of "open this URL"."""
        from motorsport_calendar.gui.views.dashboard import build_dashboard_view

        async def sentinel_handler(e):
            return None

        data = _make_dashboard_data(update=self._update(available=True, manifest=self._manifest()))
        view = build_dashboard_view(data, on_view_release=sentinel_handler)
        buttons = [c for c in _flatten_controls(view) if isinstance(c, ft.Button)]
        assert any(b.on_click is sentinel_handler for b in buttons)


class TestDashboardViewQuickAccess:
    """Sprint 53 — "Accès rapides" section: brief's named scenario."""

    def test_four_cards_present(self):
        from motorsport_calendar.gui.views.dashboard import build_dashboard_view

        view = build_dashboard_view(_make_dashboard_data())
        texts = _collect_all_text(view)
        from motorsport_calendar.gui.strings import STRINGS

        for label in (
            STRINGS.nav_weekend,
            STRINGS.nav_my_calendar,
            STRINGS.nav_search,
            STRINGS.nav_favorites,
        ):
            assert label in texts

    def test_section_header_present(self):
        from motorsport_calendar.gui.strings import STRINGS
        from motorsport_calendar.gui.views.dashboard import build_dashboard_view

        view = build_dashboard_view(_make_dashboard_data())
        texts = _collect_all_text(view)
        assert STRINGS.dashboard_section_quick_access in texts

    def test_clicking_a_card_calls_on_navigate_with_the_right_key(self):
        from motorsport_calendar.gui.views.dashboard import build_dashboard_view

        calls = []
        view = build_dashboard_view(_make_dashboard_data(), on_navigate=calls.append)
        clickable = [c for c in _flatten_controls(view) if getattr(c, "on_click", None) is not None]
        assert clickable, "expected at least one clickable quick-access card"
        for card in clickable:
            card.on_click(None)
        assert set(calls) == {"weekend", "calendar", "search", "favorites"}

    def test_no_on_navigate_does_not_crash(self):
        """Cards still render (and are inert) when on_navigate is omitted
        — e.g. a future test or a defensive default."""
        from motorsport_calendar.gui.views.dashboard import build_dashboard_view

        view = build_dashboard_view(_make_dashboard_data())
        assert isinstance(view, ft.Control)


class TestDashboardViewStatus:
    """Sprint 53 — "État de Motorsport Calendar" section: brief's named
    scenario, "informations d'état"."""

    def test_section_header_present(self):
        from motorsport_calendar.gui.strings import STRINGS
        from motorsport_calendar.gui.views.dashboard import build_dashboard_view

        view = build_dashboard_view(_make_dashboard_data())
        texts = _collect_all_text(view)
        assert STRINGS.dashboard_section_status in texts

    def test_current_version_is_shown(self):
        from motorsport_calendar.gui.views.dashboard import build_dashboard_view

        view = build_dashboard_view(_make_dashboard_data(current_version="0.2.0"))
        texts = _collect_all_text(view)
        assert "0.2.0" in texts

    def test_active_championships_is_shown(self):
        from motorsport_calendar.gui.views.dashboard import build_dashboard_view

        view = build_dashboard_view(_make_dashboard_data(active_championships=15))
        texts = _collect_all_text(view)
        assert "15" in texts

    def test_functional_providers_is_shown(self):
        from motorsport_calendar.gui.views.dashboard import build_dashboard_view

        # deliberately distinct from active_championships so the test can't
        # pass by accident if the wrong field were wired to the wrong label
        view = build_dashboard_view(
            _make_dashboard_data(active_championships=15, functional_providers=13)
        )
        texts = _collect_all_text(view)
        assert "13" in texts
        assert "15" in texts

    def test_favorite_count_is_shown(self):
        from motorsport_calendar.gui.views.dashboard import build_dashboard_view

        view = build_dashboard_view(_make_dashboard_data(favorite_count=4))
        texts = _collect_all_text(view)
        assert "4" in texts

    def test_no_value_is_hardcoded_all_four_stats_reflect_the_data(self):
        """Distinct values for every one of the 4 stats — if any label were
        wired to a fixed string instead of `data.*`, this would catch it."""
        from motorsport_calendar.gui.views.dashboard import build_dashboard_view

        view = build_dashboard_view(
            _make_dashboard_data(
                current_version="9.9.9",
                active_championships=11,
                functional_providers=7,
                favorite_count=2,
            )
        )
        texts = _collect_all_text(view)
        for expected in ("9.9.9", "11", "7", "2"):
            assert expected in texts


class TestWeekendView:
    def test_import(self):
        from motorsport_calendar.gui.views import weekend  # noqa: F401

    def test_build_returns_control(self):
        from motorsport_calendar.gui.views.weekend import build_weekend_view

        view = build_weekend_view()
        assert isinstance(view, ft.Control)

    def test_build_is_container(self):
        from motorsport_calendar.gui.views.weekend import build_weekend_view

        view = build_weekend_view()
        assert isinstance(view, ft.Container)

    def test_expand_true(self):
        from motorsport_calendar.gui.views.weekend import build_weekend_view

        view = build_weekend_view()
        assert view.expand is True

    def test_uses_shared_page_shell(self):
        from motorsport_calendar.gui.views.weekend import build_weekend_view

        view = build_weekend_view()
        assert view.content.width == theme.MAX_CONTENT_WIDTH

    def test_content_lives_inside_a_central_card(self):
        """Sprint 28: an empty placeholder page must not read as broken —
        its content sits inside one bordered central card, not loose.
        (default arg = loading state, still card-wrapped.) Sprint 31: the
        page header is now a separate PageHeader above the card, not
        absorbed into it — so we look for the card anywhere in the tree
        rather than assuming it's the only top-level section."""
        from motorsport_calendar.gui.views.weekend import build_weekend_view

        view = build_weekend_view()
        assert len(_bordered_cards(view)) == 1

    def test_loading_state_is_card_wrapped(self):
        """Sprint 29: `result=None` means the background fetch hasn't
        resolved yet."""
        from motorsport_calendar.gui.views.weekend import build_weekend_view

        view = build_weekend_view(None)
        assert len(_bordered_cards(view)) == 1

    def test_empty_state_is_card_wrapped_with_hint(self):
        from datetime import date

        from motorsport_calendar.gui.upcoming_weekend import WeekendResult
        from motorsport_calendar.gui.views.weekend import build_weekend_view

        result = WeekendResult(found=False, next_hint_date=date(2026, 8, 14))
        view = build_weekend_view(result)
        assert len(_bordered_cards(view)) == 1

    def test_page_header_is_present_above_the_content(self):
        """Sprint 31: every "Ce week-end" state shows its own PageHeader —
        no longer absorbed into the card, for consistency with every
        other page in the app."""
        from motorsport_calendar.gui.views.weekend import build_weekend_view

        view = build_weekend_view()
        column = view.content.content
        assert len(column.controls) == 2  # PageHeader, then the body

    def test_empty_state_without_hint_does_not_crash(self):
        from motorsport_calendar.gui.upcoming_weekend import WeekendResult
        from motorsport_calendar.gui.views.weekend import build_weekend_view

        result = WeekendResult(found=False, next_hint_date=None)
        view = build_weekend_view(result)
        assert isinstance(view, ft.Control)

    def test_found_state_renders_one_card_per_championship(self):
        from datetime import date

        from motorsport_calendar.gui.components.championship_card import (
            ChampionshipCardData,
            SessionRow,
        )
        from motorsport_calendar.gui.upcoming_weekend import WeekendResult
        from motorsport_calendar.gui.views.weekend import build_weekend_view

        result = WeekendResult(
            found=True,
            friday=date(2026, 7, 10),
            sunday=date(2026, 7, 12),
            cards=(
                ChampionshipCardData(
                    championship_id="formula1",
                    championship_name="Formula 1",
                    event_name="Grand Prix du Japon",
                    circuit_name="Suzuka",
                    country="🇯🇵 Japon",
                    sessions=(SessionRow("Course", "Dimanche 14:00"),),
                ),
                ChampionshipCardData(
                    championship_id="wec",
                    championship_name="FIA WEC",
                    event_name="6 Hours of Spa",
                    circuit_name="Spa",
                    country="🇧🇪 Belgique",
                    sessions=(SessionRow("Course", "Samedi 15:00"),),
                ),
            ),
        )
        view = build_weekend_view(result)
        assert len(_bordered_cards(view)) == 2

    def test_found_state_with_no_cards_does_not_crash(self):
        """Defensive: found=True with an empty cards tuple must still render."""
        from datetime import date

        from motorsport_calendar.gui.upcoming_weekend import WeekendResult
        from motorsport_calendar.gui.views.weekend import build_weekend_view

        result = WeekendResult(found=True, friday=date(2026, 7, 10), sunday=date(2026, 7, 12))
        view = build_weekend_view(result)
        assert isinstance(view, ft.Control)


class TestCalendarView:
    def _make_controls(self, **overrides):
        from motorsport_calendar.gui.views.calendar import CalendarViewControls

        defaults = {
            "year_dropdown": ft.Dropdown(label="Saison", value="2026"),
            "refresh_btn": ft.IconButton(icon=ft.Icons.REFRESH),
            "output_field": ft.TextField(label="Fichier"),
            "browse_btn": ft.IconButton(icon=ft.Icons.FOLDER_OPEN),
            "generate_btn": ft.Button(content="Créer"),
            "progress_ring": ft.ProgressRing(width=22, height=22, visible=False),
            "error_text": ft.Text(value=""),
        }
        defaults.update(overrides)
        return CalendarViewControls(**defaults)

    def _all_controls(self, control: ft.Control) -> list[ft.Control]:
        """Flatten the control tree — used to assert a given control
        instance is reachable somewhere in the built page."""
        found: list[ft.Control] = [control]
        for attr in ("controls", "content"):
            child = getattr(control, attr, None)
            if isinstance(child, list):
                for c in child:
                    found.extend(self._all_controls(c))
            elif isinstance(child, ft.Control):
                found.extend(self._all_controls(child))
        return found

    def test_import(self):
        from motorsport_calendar.gui.views import calendar  # noqa: F401

    def test_build_returns_control(self):
        from motorsport_calendar.gui.views.calendar import build_calendar_view

        view = build_calendar_view(self._make_controls())
        assert isinstance(view, ft.Control)

    def test_build_is_container(self):
        from motorsport_calendar.gui.views.calendar import build_calendar_view

        view = build_calendar_view(self._make_controls())
        assert isinstance(view, ft.Container)

    def test_expand_true(self):
        from motorsport_calendar.gui.views.calendar import build_calendar_view

        view = build_calendar_view(self._make_controls())
        assert view.expand is True

    def test_uses_shared_page_shell(self):
        from motorsport_calendar.gui.views.calendar import build_calendar_view

        view = build_calendar_view(self._make_controls())
        assert view.content.width == theme.MAX_CONTENT_WIDTH

    def test_calendar_view_controls_dataclass(self):
        from motorsport_calendar.gui.views.calendar import CalendarViewControls

        c = self._make_controls()
        assert isinstance(c, CalendarViewControls)
        assert isinstance(c.year_dropdown, ft.Dropdown)
        assert isinstance(c.category_groups, list)

    def test_default_category_groups_is_empty(self):
        c = self._make_controls()
        assert c.category_groups == []

    def test_default_selected_count_is_zero(self):
        c = self._make_controls()
        assert c.selected_count == 0

    def test_default_on_championship_click_is_noop(self):
        c = self._make_controls()
        c.on_championship_click("formula1")  # must not raise

    def test_default_on_category_toggle_is_noop(self):
        c = self._make_controls()
        c.on_category_toggle("formula", True)  # must not raise

    def test_year_dropdown_is_in_the_page_header_not_the_body(self):
        """Sprint 43: the season selector is a secondary, top-right
        control in the header (PageHeader's trailing slot) — no longer a
        step of its own. MC-002 (P0-7): the refresh button now shares
        that same trailing slot (wrapped in its own Row alongside the
        year dropdown), so both are checked for reachability within the
        header's title row rather than direct membership."""
        from motorsport_calendar.gui.views.calendar import build_calendar_view

        c = self._make_controls()
        view = build_calendar_view(c)
        # view.content.content.controls == [scrollable_region, footer] —
        # header+body are inside the scrollable region (PageContainer's
        # footer variant, Sprint 43).
        scrollable_region = view.content.content.controls[0]
        header = scrollable_region.content.controls[0]
        title_row = header.controls[0]
        assert isinstance(title_row, ft.Row)
        title_row_controls = self._all_controls(title_row)
        assert c.year_dropdown in title_row_controls
        assert c.refresh_btn in title_row_controls

    def test_footer_contains_destination_and_generate_controls(self):
        """Sprint 43: destination + "Créer" live in the fixed footer, not
        gated behind any step."""
        from motorsport_calendar.gui.views.calendar import build_calendar_view

        c = self._make_controls()
        view = build_calendar_view(c)
        footer = view.content.content.controls[-1]
        footer_controls = self._all_controls(footer)
        assert c.output_field in footer_controls
        assert c.browse_btn in footer_controls
        assert c.generate_btn in footer_controls
        assert c.progress_ring in footer_controls
        assert c.error_text in footer_controls

    def test_footer_is_outside_the_scrollable_region(self):
        from motorsport_calendar.gui.views.calendar import build_calendar_view

        c = self._make_controls()
        view = build_calendar_view(c)
        outer_column = view.content.content
        scrollable_region = outer_column.controls[0]
        assert c.generate_btn not in self._all_controls(scrollable_region)

    def test_championships_section_is_first_in_the_scrollable_body(self):
        """Sprint 43, requirement 1: championships are the page's entry
        point, immediately under the title."""
        from motorsport_calendar.gui.components.championship_selector import (
            ChampionshipButtonData,
            ChampionshipCategoryData,
        )
        from motorsport_calendar.gui.views.calendar import build_calendar_view

        groups = [
            ChampionshipCategoryData(
                category_id="formula",
                label="🏎  Formula",
                expanded=True,
                options=(
                    ChampionshipButtonData(
                        championship_id="formula1", display_name="Formula 1", selected=True
                    ),
                ),
            )
        ]
        c = self._make_controls(category_groups=groups, season_groups=())
        view = build_calendar_view(c)
        scrollable_region = view.content.content.controls[0]
        scrollable_column = scrollable_region.content
        # controls[0] is the PageHeader (title); the first *body* item —
        # immediately under the title, per requirement 1 — is controls[1].
        first_body_item = scrollable_column.controls[1]
        assert "Formula 1" in self._texts(first_body_item)

    def _texts(self, control: ft.Control) -> list[str]:
        found: list[str] = []
        if isinstance(control, ft.Text) and control.value:
            found.append(str(control.value))
        # "title" — ft.ExpansionTile (Sprint 43) keeps its title separate
        # from "controls" (its expandable body) and "content".
        for attr in ("controls", "content", "title"):
            child = getattr(control, attr, None)
            if isinstance(child, list):
                for c in child:
                    found.extend(self._texts(c))
            elif isinstance(child, ft.Control):
                found.extend(self._texts(child))
        return found


class TestCalendarViewSelectionSummary:
    """Sprint 40 — the persistent selection summary block ("Mon calendrier"
    as a browsable calendar). Sprint 43: now permanently visible on the
    single reorganized page (no more per-step gating), and always shows
    the championship count (known instantly, independent of the fetch
    that the rest of the summary depends on)."""

    def _make_controls(self, **overrides):
        return TestCalendarView()._make_controls(**overrides)

    def _texts(self, control: ft.Control) -> list[str]:
        found: list[str] = []
        if isinstance(control, ft.Text) and control.value:
            found.append(str(control.value))
        # "title" — ft.ExpansionTile (Sprint 43) keeps its title separate
        # from "controls" (its expandable body) and "content".
        for attr in ("controls", "content", "title"):
            child = getattr(control, attr, None)
            if isinstance(child, list):
                for c in child:
                    found.extend(self._texts(c))
            elif isinstance(child, ft.Control):
                found.extend(self._texts(child))
        return found

    def test_default_selection_summary_is_none(self):
        c = self._make_controls()
        assert c.selection_summary is None

    def test_loading_state_shows_progress_ring_and_loading_text(self):
        from motorsport_calendar.gui.strings import STRINGS
        from motorsport_calendar.gui.views.calendar import _selection_summary_block

        block = _selection_summary_block(None, 3)
        texts = self._texts(block)
        assert STRINGS.calendar_summary_loading in texts
        assert _bordered_cards(block)  # rendered inside theme.card()

    def test_loading_state_still_shows_championship_count(self):
        """Sprint 43: the count is known instantly (len of a list), so it
        is shown even while the rest of the summary is still fetching."""
        from motorsport_calendar.gui.views.calendar import _selection_summary_block

        block = _selection_summary_block(None, 3)
        texts = self._texts(block)
        assert "3" in texts

    def test_empty_selection_shows_empty_message(self):
        from motorsport_calendar.gui.calendar_selection import SelectionSummary
        from motorsport_calendar.gui.strings import STRINGS
        from motorsport_calendar.gui.views.calendar import _selection_summary_block

        summary = SelectionSummary(
            event_count=0, session_count=0, period_start=None, period_end=None
        )
        block = _selection_summary_block(summary, 0)
        texts = self._texts(block)
        assert STRINGS.calendar_summary_empty_selection in texts

    def test_populated_selection_shows_counts_and_period(self):
        from datetime import date

        from motorsport_calendar.gui.calendar_selection import SelectionSummary
        from motorsport_calendar.gui.views.calendar import _selection_summary_block

        summary = SelectionSummary(
            event_count=26,
            session_count=126,
            period_start=date(2026, 2, 11),
            period_end=date(2026, 12, 6),
        )
        block = _selection_summary_block(summary, 2)
        texts = self._texts(block)
        assert "2" in texts
        assert "26" in texts
        assert "126" in texts
        assert "11/02/2026 - 06/12/2026" in texts

    def test_populated_selection_singular_plural_strings(self):
        from datetime import date

        from motorsport_calendar.gui.calendar_selection import SelectionSummary
        from motorsport_calendar.gui.views.calendar import _selection_summary_block

        singular = SelectionSummary(
            event_count=1,
            session_count=1,
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 1),
        )
        texts = self._texts(_selection_summary_block(singular, 1))
        assert "Championnat" in texts
        assert "Événement" in texts
        assert "Session" in texts

    def test_populated_selection_plural_championships(self):
        from datetime import date

        from motorsport_calendar.gui.calendar_selection import SelectionSummary
        from motorsport_calendar.gui.views.calendar import _selection_summary_block

        summary = SelectionSummary(
            event_count=5,
            session_count=10,
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 1),
        )
        texts = self._texts(_selection_summary_block(summary, 3))
        assert "Championnats" in texts

    def test_populated_selection_without_period_shows_placeholder(self):
        from motorsport_calendar.gui.calendar_selection import SelectionSummary
        from motorsport_calendar.gui.strings import STRINGS
        from motorsport_calendar.gui.views.calendar import _selection_summary_block

        summary = SelectionSummary(
            event_count=2, session_count=0, period_start=None, period_end=None
        )
        block = _selection_summary_block(summary, 1)
        texts = self._texts(block)
        assert STRINGS.calendar_summary_period_empty in texts

    def test_build_calendar_view_includes_summary_block(self):
        from motorsport_calendar.gui.calendar_selection import SelectionSummary
        from motorsport_calendar.gui.views.calendar import build_calendar_view

        summary = SelectionSummary(
            event_count=5, session_count=10, period_start=None, period_end=None
        )
        c = self._make_controls(selection_summary=summary, selected_count=2)
        view = build_calendar_view(c)
        assert "2" in self._texts(view)
        assert "5" in self._texts(view)
        assert "10" in self._texts(view)


class TestCalendarViewSeasonExplorer:
    """Sprint 41 — the season explorer (event list, sorted chronologically,
    grouped by month), rendered below the permanent selection summary.
    Sprint 43: only shown once >= 1 championship is selected (an empty
    tuple — the same signal as "nothing selected" — renders an
    EmptyState, already covered by test_empty_groups_shows_empty_state)."""

    def _make_controls(self, **overrides):
        return TestCalendarView()._make_controls(**overrides)

    def _texts(self, control: ft.Control) -> list[str]:
        return TestCalendarViewSelectionSummary()._texts(control)

    def _row(self, **overrides):
        from motorsport_calendar.gui.season_explorer import SeasonEventRow

        defaults = {
            "event_name": "Belgian Grand Prix",
            "championship_name": "Formula 1",
            "circuit_name": "Spa-Francorchamps",
            "country": "🇧🇪 Belgique",
            "date_label": "Dimanche 12/07",
            "championship_id": "formula1",
            "event_uid": "formula1-1@test",
        }
        defaults.update(overrides)
        return SeasonEventRow(**defaults)

    def test_default_season_groups_is_none(self):
        c = self._make_controls()
        assert c.season_groups is None

    def test_loading_state_shows_progress_ring_and_loading_text(self):
        from motorsport_calendar.gui.strings import STRINGS
        from motorsport_calendar.gui.views.calendar import _season_explorer_block

        block = _season_explorer_block(None, lambda row: None)
        texts = self._texts(block)
        assert STRINGS.calendar_season_explorer_loading in texts
        assert _bordered_cards(block)  # rendered inside theme.card()

    def test_empty_groups_shows_empty_state(self):
        from motorsport_calendar.gui.strings import STRINGS
        from motorsport_calendar.gui.views.calendar import _season_explorer_block

        block = _season_explorer_block((), lambda row: None)
        texts = self._texts(block)
        assert STRINGS.calendar_season_explorer_empty in texts

    def test_populated_groups_show_month_label_and_event_fields(self):
        from motorsport_calendar.gui.season_explorer import SeasonMonthGroup
        from motorsport_calendar.gui.views.calendar import _season_explorer_block

        groups = (SeasonMonthGroup(month_label="Juillet 2026", rows=(self._row(),)),)
        block = _season_explorer_block(groups, lambda row: None)
        texts = self._texts(block)
        assert "Juillet 2026" in texts
        assert "Belgian Grand Prix" in texts
        assert "Formula 1" in texts
        assert "Spa-Francorchamps" in texts
        assert "🇧🇪 Belgique" in texts
        assert "Dimanche 12/07" in texts

    def test_event_row_omits_circuit_and_country_lines_when_none(self):
        from motorsport_calendar.gui.season_explorer import SeasonMonthGroup
        from motorsport_calendar.gui.views.calendar import _season_explorer_block

        row = self._row(circuit_name=None, country=None)
        groups = (SeasonMonthGroup(month_label="Juillet 2026", rows=(row,)),)
        block = _season_explorer_block(groups, lambda row: None)
        texts = self._texts(block)
        assert "Belgian Grand Prix" in texts
        assert "Spa-Francorchamps" not in texts
        assert "🇧🇪 Belgique" not in texts

    def test_multiple_month_groups_all_rendered(self):
        from motorsport_calendar.gui.season_explorer import SeasonMonthGroup
        from motorsport_calendar.gui.views.calendar import _season_explorer_block

        groups = (
            SeasonMonthGroup(month_label="Mars 2026", rows=(self._row(event_name="First"),)),
            SeasonMonthGroup(month_label="Avril 2026", rows=(self._row(event_name="Second"),)),
        )
        block = _season_explorer_block(groups, lambda row: None)
        texts = self._texts(block)
        assert "Mars 2026" in texts
        assert "Avril 2026" in texts
        assert "First" in texts
        assert "Second" in texts

    def test_clicking_a_row_calls_on_event_click_with_that_row(self):
        from motorsport_calendar.gui.views.calendar import _season_event_row

        clicked: list = []
        row = self._row()
        card = _season_event_row(row, clicked.append)
        assert card.on_click is not None
        card.on_click(None)  # simulate a Flet click event
        assert clicked == [row]

    def test_default_on_event_click_is_noop(self):
        c = self._make_controls()
        c.on_event_click(self._row())  # must not raise

    def test_build_calendar_view_wires_on_event_click_into_rows(self):
        from motorsport_calendar.gui.season_explorer import SeasonMonthGroup
        from motorsport_calendar.gui.views.calendar import build_calendar_view

        clicked: list = []
        row = self._row()
        groups = (SeasonMonthGroup(month_label="Juillet 2026", rows=(row,)),)
        c = self._make_controls(season_groups=groups, on_event_click=clicked.append)

        def _find_event_row_card(control: ft.Control) -> ft.Container | None:
            """The step indicator also has clickable containers (Sprint 26)
            — find specifically the card that renders the event's name."""
            if (
                isinstance(control, ft.Container)
                and control.on_click is not None
                and row.event_name in self._texts(control)
            ):
                return control
            for attr in ("controls", "content"):
                child = getattr(control, attr, None)
                if isinstance(child, list):
                    for child_ctrl in child:
                        found = _find_event_row_card(child_ctrl)
                        if found is not None:
                            return found
                elif isinstance(child, ft.Control):
                    found = _find_event_row_card(child)
                    if found is not None:
                        return found
            return None

        view = build_calendar_view(c)
        card = _find_event_row_card(view)
        assert card is not None
        card.on_click(None)
        assert clicked == [row]

    def test_build_calendar_view_includes_season_explorer(self):
        from motorsport_calendar.gui.season_explorer import SeasonMonthGroup
        from motorsport_calendar.gui.views.calendar import build_calendar_view

        groups = (SeasonMonthGroup(month_label="Juillet 2026", rows=(self._row(),)),)
        c = self._make_controls(season_groups=groups)
        view = build_calendar_view(c)
        assert "Belgian Grand Prix" in self._texts(view)

    def test_build_calendar_view_shows_empty_state_when_nothing_selected(self):
        """Sprint 43, requirement 6: an empty selection renders an
        EmptyState instead of the explorer, without needing any new
        signal — season_groups=() already means exactly this."""
        from motorsport_calendar.gui.strings import STRINGS
        from motorsport_calendar.gui.views.calendar import build_calendar_view

        c = self._make_controls(season_groups=())
        view = build_calendar_view(c)
        assert STRINGS.calendar_season_explorer_empty in self._texts(view)


class TestFavoritesView:
    """Sprint 44 — "Mes favoris" becomes a real page: every registered
    championship, grouped by category, reusing the exact same
    accordion-of-buttons UI as "Mon calendrier" (Sprint 43) via
    ``gui/components/championship_selector.py``, wired to "favorited"
    instead of "selected for generation"."""

    def _texts(self, control: ft.Control) -> list[str]:
        found: list[str] = []
        if isinstance(control, ft.Text) and control.value:
            found.append(str(control.value))
        for attr in ("controls", "content", "title"):
            child = getattr(control, attr, None)
            if isinstance(child, list):
                for c in child:
                    found.extend(self._texts(c))
            elif isinstance(child, ft.Control):
                found.extend(self._texts(child))
        return found

    def _groups(self, **overrides):
        from motorsport_calendar.gui.components.championship_selector import (
            ChampionshipButtonData,
            ChampionshipCategoryData,
        )

        defaults = {
            "category_id": "formula",
            "label": "🏎  Formula",
            "expanded": True,
            "options": (
                ChampionshipButtonData(
                    championship_id="formula1", display_name="Formula 1", selected=True
                ),
                ChampionshipButtonData(
                    championship_id="formula2", display_name="Formula 2", selected=False
                ),
            ),
        }
        defaults.update(overrides)
        return [ChampionshipCategoryData(**defaults)]

    def test_import(self):
        from motorsport_calendar.gui.views import favorites  # noqa: F401

    def test_build_returns_control(self):
        from motorsport_calendar.gui.views.favorites import build_favorites_view

        view = build_favorites_view(self._groups(), 1, lambda cid: None, lambda c, e: None)
        assert isinstance(view, ft.Control)

    def test_expand_true(self):
        from motorsport_calendar.gui.views.favorites import build_favorites_view

        view = build_favorites_view(self._groups(), 1, lambda cid: None, lambda c, e: None)
        assert view.expand is True

    def test_uses_shared_page_shell(self):
        from motorsport_calendar.gui.views.favorites import build_favorites_view

        view = build_favorites_view(self._groups(), 1, lambda cid: None, lambda c, e: None)
        assert view.content.width == theme.MAX_CONTENT_WIDTH

    def test_shows_championships_from_the_groups(self):
        from motorsport_calendar.gui.views.favorites import build_favorites_view

        view = build_favorites_view(self._groups(), 1, lambda cid: None, lambda c, e: None)
        texts = self._texts(view)
        assert "Formula 1" in texts
        assert "Formula 2" in texts

    def test_subtitle_shows_favorite_count(self):
        from motorsport_calendar.gui.views.favorites import build_favorites_view

        view = build_favorites_view(self._groups(), 3, lambda cid: None, lambda c, e: None)
        assert "3 favoris" in self._texts(view)

    def test_body_is_only_header_and_championship_selector(self):
        """The brief explicitly says "aucun nouveau composant si ceux
        existants suffisent" — nothing but PageHeader + the shared
        championship selector, no extra wrapping/section of its own."""
        from motorsport_calendar.gui.views.favorites import build_favorites_view

        view = build_favorites_view(self._groups(), 1, lambda cid: None, lambda c, e: None)
        column = view.content.content
        assert len(column.controls) == 2  # PageHeader, then the selector
        assert isinstance(column.controls[1], ft.Column)  # Section(...) shape

    def test_clicking_a_championship_calls_on_favorite_click(self):
        from motorsport_calendar.gui.views.favorites import build_favorites_view

        clicked: list[str] = []
        view = build_favorites_view(self._groups(), 1, clicked.append, lambda c, e: None)

        def _find_button(control: ft.Control) -> ft.Container | None:
            if (
                isinstance(control, ft.Container)
                and control.on_click is not None
                and "Formula 2" in self._texts(control)
            ):
                return control
            for attr in ("controls", "content"):
                child = getattr(control, attr, None)
                if isinstance(child, list):
                    for c in child:
                        found = _find_button(c)
                        if found is not None:
                            return found
                elif isinstance(child, ft.Control):
                    found = _find_button(child)
                    if found is not None:
                        return found
            return None

        button = _find_button(view)
        assert button is not None
        button.on_click(None)
        assert clicked == ["formula2"]

    def test_header_icon_matches_the_nav_rails_filled_star(self):
        """Sprint 54: the header used to show STAR_BORDER, a third star
        glyph distinct from both the nav rail's STAR_OUTLINE (unselected)
        and STAR (selected) — every other page's header icon matches its
        nav rail's filled/selected variant, this page now does too."""
        from motorsport_calendar.gui.views.favorites import build_favorites_view

        view = build_favorites_view(self._groups(), 1, lambda cid: None, lambda c, e: None)
        column = view.content.content
        header = column.controls[0]
        icon_row = header.controls[0]
        icon = next(c for c in icon_row.controls if isinstance(c, ft.Icon))
        assert icon.icon == ft.Icons.STAR


class TestSearchView:
    """Sprint 45 — "Recherche" is pure layout: a pre-built search field
    plus already-searched/grouped/sorted ``SearchResults`` handed in by
    main_view.py (via ``gui/search_service.py``). This view never
    searches, sorts, or decides what "matches" — it only arranges."""

    def _texts(self, control: ft.Control) -> list[str]:
        found: list[str] = []
        if isinstance(control, ft.Text) and control.value:
            found.append(str(control.value))
        for attr in ("controls", "content", "title"):
            child = getattr(control, attr, None)
            if isinstance(child, list):
                for c in child:
                    found.extend(self._texts(c))
            elif isinstance(child, ft.Control):
                found.extend(self._texts(child))
        return found

    def _item(self, title: str, subtitle: str | None = None, **identity):
        from motorsport_calendar.gui.search_service import SearchResultItem

        return SearchResultItem(title=title, subtitle=subtitle, **identity)

    def _find_card(self, control: ft.Control, title: str) -> ft.Container | None:
        if (
            isinstance(control, ft.Container)
            and control.on_click is not None
            and title in self._texts(control)
        ):
            return control
        for attr in ("controls", "content"):
            child = getattr(control, attr, None)
            if isinstance(child, list):
                for c in child:
                    found = self._find_card(c, title)
                    if found is not None:
                        return found
            elif isinstance(child, ft.Control):
                found = self._find_card(child, title)
                if found is not None:
                    return found
        return None

    def test_import(self):
        from motorsport_calendar.gui.views import search  # noqa: F401

    def test_build_returns_control(self):
        from motorsport_calendar.gui.views.search import build_search_view

        view = build_search_view(ft.TextField(), SearchResults(), False)
        assert isinstance(view, ft.Control)

    def test_expand_true(self):
        from motorsport_calendar.gui.views.search import build_search_view

        view = build_search_view(ft.TextField(), SearchResults(), False)
        assert view.expand is True

    def test_uses_shared_page_shell(self):
        from motorsport_calendar.gui.views.search import build_search_view

        view = build_search_view(ft.TextField(), SearchResults(), False)
        assert view.content.width == theme.MAX_CONTENT_WIDTH

    def test_header_uses_search_icon(self):
        from motorsport_calendar.gui.views.search import build_search_view

        view = build_search_view(ft.TextField(), SearchResults(), False)
        column = view.content.content
        header = column.controls[0]
        icon_row = header.controls[0]
        icon = next(c for c in icon_row.controls if isinstance(c, ft.Icon))
        assert icon.icon == ft.Icons.SEARCH

    def test_search_field_is_first_in_the_body(self):
        from motorsport_calendar.gui.views.search import build_search_view

        field = ft.TextField()
        view = build_search_view(field, SearchResults(), False)
        column = view.content.content
        assert column.controls[1] is field

    def test_empty_query_shows_the_empty_query_empty_state(self):
        """ "recherche vide" validation scenario — nothing typed yet."""
        from motorsport_calendar.gui.strings import STRINGS
        from motorsport_calendar.gui.views.search import build_search_view

        view = build_search_view(ft.TextField(), SearchResults(), False)
        assert STRINGS.search_empty_query in self._texts(view)
        assert STRINGS.search_no_results not in self._texts(view)

    def test_query_with_no_results_shows_the_no_results_empty_state(self):
        """ "aucun résultat" validation scenario — searched, found nothing."""
        from motorsport_calendar.gui.strings import STRINGS
        from motorsport_calendar.gui.views.search import build_search_view

        view = build_search_view(ft.TextField(), SearchResults(), True)
        assert STRINGS.search_no_results in self._texts(view)
        assert STRINGS.search_empty_query not in self._texts(view)

    def test_no_subtitle_when_query_is_empty(self):
        from motorsport_calendar.gui.views.search import build_search_view

        view = build_search_view(ft.TextField(), SearchResults(), False)
        header = view.content.content.controls[0]
        assert "résultat" not in " ".join(self._texts(header))

    def test_no_subtitle_when_query_has_no_results(self):
        from motorsport_calendar.gui.views.search import build_search_view

        view = build_search_view(ft.TextField(), SearchResults(), True)
        header = view.content.content.controls[0]
        assert "résultat" not in " ".join(self._texts(header))

    def test_subtitle_shows_result_count_when_query_has_results(self):
        from motorsport_calendar.gui.views.search import build_search_view

        results = SearchResults(championships=(self._item("Formula 1"),))
        view = build_search_view(ft.TextField(), results, True)
        assert "1 résultat" in self._texts(view)

    def test_subtitle_pluralizes_result_count(self):
        from motorsport_calendar.gui.views.search import build_search_view

        results = SearchResults(championships=(self._item("Formula 1"), self._item("Formula 2")))
        view = build_search_view(ft.TextField(), results, True)
        assert "2 résultats" in self._texts(view)

    def test_shows_championships_section_with_its_items(self):
        from motorsport_calendar.gui.strings import STRINGS
        from motorsport_calendar.gui.views.search import build_search_view

        results = SearchResults(championships=(self._item("Formula 1"),))
        view = build_search_view(ft.TextField(), results, True)
        texts = self._texts(view)
        assert STRINGS.search_section_championships in texts
        assert "Formula 1" in texts

    def test_shows_events_section_with_its_items_and_subtitle(self):
        from motorsport_calendar.gui.strings import STRINGS
        from motorsport_calendar.gui.views.search import build_search_view

        results = SearchResults(events=(self._item("Belgian Grand Prix", "Formula 1"),))
        view = build_search_view(ft.TextField(), results, True)
        texts = self._texts(view)
        assert STRINGS.search_section_events in texts
        assert "Belgian Grand Prix" in texts
        assert "Formula 1" in texts

    def test_shows_circuits_section_with_its_items(self):
        from motorsport_calendar.gui.strings import STRINGS
        from motorsport_calendar.gui.views.search import build_search_view

        results = SearchResults(circuits=(self._item("Spa-Francorchamps", "Belgique"),))
        view = build_search_view(ft.TextField(), results, True)
        texts = self._texts(view)
        assert STRINGS.search_section_circuits in texts
        assert "Spa-Francorchamps" in texts

    def test_omits_sections_with_no_items(self):
        from motorsport_calendar.gui.strings import STRINGS
        from motorsport_calendar.gui.views.search import build_search_view

        results = SearchResults(championships=(self._item("Formula 1"),))
        view = build_search_view(ft.TextField(), results, True)
        texts = self._texts(view)
        assert STRINGS.search_section_events not in texts
        assert STRINGS.search_section_circuits not in texts

    def test_shows_all_three_sections_when_all_have_results(self):
        from motorsport_calendar.gui.strings import STRINGS
        from motorsport_calendar.gui.views.search import build_search_view

        results = SearchResults(
            championships=(self._item("Formula 1"),),
            events=(self._item("Belgian Grand Prix", "Formula 1"),),
            circuits=(self._item("Spa-Francorchamps", "Belgique"),),
        )
        view = build_search_view(ft.TextField(), results, True)
        texts = self._texts(view)
        assert STRINGS.search_section_championships in texts
        assert STRINGS.search_section_events in texts
        assert STRINGS.search_section_circuits in texts

    def test_clicking_a_championship_result_calls_on_championship_click(self):
        """Sprint 55 — "clic championnat" validation scenario."""
        from motorsport_calendar.gui.views.search import build_search_view

        item = self._item("Formula 1", championship_id="formula1")
        results = SearchResults(championships=(item,))
        clicked: list = []
        view = build_search_view(
            ft.TextField(), results, True, on_championship_click=clicked.append
        )
        card = self._find_card(view, "Formula 1")
        assert card is not None
        card.on_click(None)
        assert clicked == [item]

    def test_clicking_an_event_result_calls_on_event_click(self):
        """Sprint 55 — "clic événement" validation scenario."""
        from motorsport_calendar.gui.views.search import build_search_view

        item = self._item(
            "Belgian Grand Prix",
            "Formula 1",
            championship_id="formula1",
            event_uid="formula1-belgian@test",
        )
        results = SearchResults(events=(item,))
        clicked: list = []
        view = build_search_view(ft.TextField(), results, True, on_event_click=clicked.append)
        card = self._find_card(view, "Belgian Grand Prix")
        assert card is not None
        card.on_click(None)
        assert clicked == [item]

    def test_clicking_a_circuit_result_calls_on_circuit_click(self):
        """Sprint 55 — "clic circuit" validation scenario."""
        from motorsport_calendar.gui.views.search import build_search_view

        item = self._item("Spa-Francorchamps", "Belgique", circuit_key="spa-francorchamps")
        results = SearchResults(circuits=(item,))
        clicked: list = []
        view = build_search_view(ft.TextField(), results, True, on_circuit_click=clicked.append)
        card = self._find_card(view, "Spa-Francorchamps")
        assert card is not None
        card.on_click(None)
        assert clicked == [item]

    def test_clicking_one_kind_never_calls_another_kinds_callback(self):
        """A championship click must never also fire the event/circuit
        handlers (and vice versa) — each section is wired independently."""
        from motorsport_calendar.gui.views.search import build_search_view

        results = SearchResults(
            championships=(self._item("Formula 1", championship_id="formula1"),),
        )
        championship_clicks: list = []
        event_clicks: list = []
        circuit_clicks: list = []
        view = build_search_view(
            ft.TextField(),
            results,
            True,
            on_championship_click=championship_clicks.append,
            on_event_click=event_clicks.append,
            on_circuit_click=circuit_clicks.append,
        )
        card = self._find_card(view, "Formula 1")
        assert card is not None
        card.on_click(None)
        assert len(championship_clicks) == 1
        assert event_clicks == []
        assert circuit_clicks == []

    def test_results_are_not_clickable_when_no_callback_is_given(self):
        """ "absence de résultat" — no callback wired (e.g. the initial,
        unwired build) must never crash and must never render a
        clickable card."""
        from motorsport_calendar.gui.views.search import build_search_view

        item = self._item("Formula 1", championship_id="formula1")
        results = SearchResults(championships=(item,))
        view = build_search_view(ft.TextField(), results, True)
        card = self._find_card(view, "Formula 1")
        assert card is None

    def test_empty_results_render_no_clickable_cards(self):
        """ "absence de résultat" validation scenario — nothing to click
        when there is nothing to show, callbacks wired or not."""
        from motorsport_calendar.gui.views.search import build_search_view

        view = build_search_view(
            ft.TextField(),
            SearchResults(),
            True,
            on_championship_click=lambda item: None,
            on_event_click=lambda item: None,
            on_circuit_click=lambda item: None,
        )
        clickable = [c for c in _flatten_controls(view) if getattr(c, "on_click", None)]
        assert clickable == []


class TestPreferencesView:
    """Sprint 52 — real configuration center. main_view.py builds every
    Flet control (Switch/Dropdown) with its handler already wired; this
    view only lays them out, so tests here build a minimal, unwired
    ``PreferencesViewControls`` instance (no handler needed to verify
    layout)."""

    def _make_controls(self, **overrides):
        from motorsport_calendar.gui.views.preferences import PreferencesViewControls

        defaults = {
            "update_check_enabled_switch": ft.Switch(value=True),
            "default_year_dropdown": ft.Dropdown(value="current"),
            "ics_alarm_minutes_dropdown": ft.Dropdown(value="30"),
        }
        defaults.update(overrides)
        return PreferencesViewControls(**defaults)

    def test_import(self):
        from motorsport_calendar.gui.views import preferences  # noqa: F401

    def test_build_returns_control(self):
        from motorsport_calendar.gui.views.preferences import build_preferences_view

        view = build_preferences_view(self._make_controls())
        assert isinstance(view, ft.Control)

    def test_build_with_custom_application_model(self):
        from motorsport_calendar.gui.views.preferences import build_preferences_view

        model = PreferencesModel(theme="light", language="en", time_format="12h")
        view = build_preferences_view(self._make_controls(application=model))
        assert isinstance(view, ft.Control)

    def test_expand_true(self):
        from motorsport_calendar.gui.views.preferences import build_preferences_view

        view = build_preferences_view(self._make_controls())
        assert view.expand is True

    def test_pref_rows_count(self):
        """Application section only — Notifications/Mises à jour/Calendrier
        are real controls now, not "coming soon" rows (Sprint 52)."""
        from motorsport_calendar.gui.views.preferences import _PREF_ROWS

        assert len(_PREF_ROWS) == 3

    def test_pref_rows_structure(self):
        from motorsport_calendar.gui.views.preferences import _PREF_ROWS

        for icon, label, field_name in _PREF_ROWS:
            assert icon is not None
            assert isinstance(label, str)
            assert len(label) > 0
            assert hasattr(PreferencesModel, field_name) or hasattr(PreferencesModel(), field_name)

    def test_uses_shared_page_shell(self):
        from motorsport_calendar.gui.views.preferences import build_preferences_view

        view = build_preferences_view(self._make_controls())
        assert view.content.width == theme.MAX_CONTENT_WIDTH

    def test_rows_render_as_bordered_cards(self):
        """3 real control rows (1 update + 2 calendar), each its own
        single bordered card; 6 "coming soon" rows (3 notifications,
        MC-002 P0-2, + 3 Application), each a bordered card PLUS a
        bordered chip (2 each) — same "no single outer card" Layout
        System convention as every other page since Sprint 31."""
        from motorsport_calendar.gui.views.preferences import build_preferences_view

        view = build_preferences_view(self._make_controls())
        assert len(_bordered_cards(view)) == 3 * 1 + 6 * 2

    def test_page_header_is_present_above_the_sections(self):
        from motorsport_calendar.gui.views.preferences import build_preferences_view

        view = build_preferences_view(self._make_controls())
        column = view.content.content
        # PageHeader, then one Section per group (Notifications/Mises à
        # jour/Calendrier/Application).
        assert len(column.controls) == 5

    def test_pref_rows_now_carry_their_own_border(self):
        """Sprint 31: rows are no longer nested inside one big outer card
        (that card is gone — PageHeader is now separate from the body), so
        each row can safely be its own bordered card again, uniformly via
        CardList. Sprint 57: the row itself is now the shared
        ``ComingSoonRow`` component, not a private helper of this module."""
        from motorsport_calendar.gui.components.layout import ComingSoonRow

        row = ComingSoonRow(ft.Icons.LANGUAGE, "Langue")
        assert isinstance(row, ft.Container)
        assert row.border is not None

    def test_notifications_section_is_all_coming_soon_rows(self):
        """MC-002 (P0-2) regression guard: the Notifications section must
        never render a live Switch/Dropdown again — Flet has no OS
        notification backend, so a working-looking toggle that silently
        never notifies was a P0 blocker (MC-001 §5/§6). Only the 3
        remaining real controls (update/default_year/ics_alarm) should
        exist — none of them under the Notifications section."""
        from motorsport_calendar.gui.strings import STRINGS
        from motorsport_calendar.gui.views.preferences import build_preferences_view

        view = build_preferences_view(self._make_controls())
        all_controls = _flatten_controls(view)
        assert sum(isinstance(c, ft.Switch) for c in all_controls) == 1
        assert sum(isinstance(c, ft.Dropdown) for c in all_controls) == 2
        texts = _collect_all_text(view)
        assert texts.count(STRINGS.prefs_coming_soon) == 6  # 3 notifications + 3 application

    def test_switches_and_dropdowns_are_present_uncloned(self):
        """The pre-built controls (with their on_change/on_select handlers
        already wired by main_view.py) must be the exact objects rendered
        — never rebuilt/cloned by the view, which would silently drop the
        wiring."""
        from motorsport_calendar.gui.views.preferences import build_preferences_view

        controls = self._make_controls()
        view = build_preferences_view(controls)
        all_controls = _flatten_controls(view)
        assert controls.update_check_enabled_switch in all_controls
        assert controls.default_year_dropdown in all_controls
        assert controls.ics_alarm_minutes_dropdown in all_controls


class TestAboutView:
    def test_import(self):
        from motorsport_calendar.gui.views import about  # noqa: F401

    def test_build_returns_control(self):
        from motorsport_calendar.gui.views.about import build_about_view

        launcher = ft.UrlLauncher()
        view = build_about_view(launcher)
        assert isinstance(view, ft.Control)

    def test_github_url_defined(self):
        from motorsport_calendar.gui.views.about import _GITHUB_URL

        assert _GITHUB_URL.startswith("https://github.com/")

    def test_expand_true(self):
        from motorsport_calendar.gui.views.about import build_about_view

        view = build_about_view(ft.UrlLauncher())
        assert view.expand is True

    def test_uses_shared_page_shell(self):
        from motorsport_calendar.gui.views.about import build_about_view

        view = build_about_view(ft.UrlLauncher())
        assert view.content.width == theme.MAX_CONTENT_WIDTH

    def test_content_is_not_wrapped_in_a_card(self):
        """Sprint 28 task 3 reorganizes À propos compactly — unlike the 3
        empty placeholder pages, it does not get a card wrapper."""
        from motorsport_calendar.gui.views.about import build_about_view

        view = build_about_view(ft.UrlLauncher())
        column = view.content.content
        for section in column.controls:
            assert not (isinstance(section, ft.Container) and section.border is not None)

    def test_app_title_and_version_shown_once(self):
        """The generic "À propos" label is gone — the app name/version
        block is now the page's own heading, shown exactly once."""
        from motorsport_calendar.gui.strings import STRINGS
        from motorsport_calendar.gui.views.about import build_about_view

        view = build_about_view(ft.UrlLauncher())

        texts = _collect_all_text(view)
        assert texts.count(STRINGS.app_title) == 1

    def test_default_version_is_the_real_package_version(self):
        """Sprint 54: no version parameter -> the actual
        motorsport_calendar.__version__, not a placeholder — same value
        the Dashboard's "État" section already shows (Sprint 53)."""
        from motorsport_calendar import __version__
        from motorsport_calendar.gui.strings import STRINGS
        from motorsport_calendar.gui.views.about import build_about_view

        view = build_about_view(ft.UrlLauncher())
        texts = _collect_all_text(view)
        assert STRINGS.about_version.format(version=__version__) in texts

    def test_version_override_is_shown(self):
        from motorsport_calendar.gui.strings import STRINGS
        from motorsport_calendar.gui.views.about import build_about_view

        view = build_about_view(ft.UrlLauncher(), version="9.9.9")
        texts = _collect_all_text(view)
        assert STRINGS.about_version.format(version="9.9.9") in texts

    def test_shows_objectives_section_with_every_objective(self):
        """Sprint 57 (Préparation Beta — positionnement): À propos becomes
        a real project presentation, starting with its objectives."""
        from motorsport_calendar.gui.strings import STRINGS
        from motorsport_calendar.gui.views.about import build_about_view

        view = build_about_view(ft.UrlLauncher())
        texts = " ".join(_collect_all_text(view))
        assert STRINGS.about_section_objectives in texts
        for objective in STRINGS.about_objectives:
            assert objective in texts

    def test_shows_open_source_philosophy_section(self):
        from motorsport_calendar.gui.strings import STRINGS
        from motorsport_calendar.gui.views.about import build_about_view

        view = build_about_view(ft.UrlLauncher())
        texts = _collect_all_text(view)
        assert STRINGS.about_section_open_source in texts
        assert STRINGS.about_open_source_text in texts

    def test_shows_technologies_section_with_every_technology(self):
        from motorsport_calendar.gui.strings import STRINGS
        from motorsport_calendar.gui.views.about import build_about_view

        view = build_about_view(ft.UrlLauncher())
        texts = _collect_all_text(view)
        assert STRINGS.about_section_tech in texts
        for tech in STRINGS.about_tech_stack:
            assert tech in texts

    def test_github_button_uses_the_shared_url_opener(self):
        """Sprint 57 (nettoyage): the GitHub link's on_click now comes
        from ``gui/url_opener.py::make_url_opener`` — proven by patching
        it and checking it was called with url_launcher/_GITHUB_URL."""
        from unittest.mock import patch

        from motorsport_calendar.gui.views.about import _GITHUB_URL, build_about_view

        launcher = ft.UrlLauncher()
        with patch("motorsport_calendar.gui.views.about.make_url_opener") as mock_make_opener:
            build_about_view(launcher)
        mock_make_opener.assert_called_once_with(launcher, _GITHUB_URL)


class TestSupportView:
    """Sprint 57 (Préparation Beta — positionnement): "Soutenir le
    projet" — the contact point between Motorsport Calendar and its
    community. Purely informative: no local vote system, no local
    donation system, no local suggestion form."""

    def test_import(self):
        from motorsport_calendar.gui.views import support  # noqa: F401

    def test_build_returns_control(self):
        from motorsport_calendar.gui.views.support import build_support_view

        view = build_support_view(ft.UrlLauncher())
        assert isinstance(view, ft.Control)

    def test_expand_true(self):
        from motorsport_calendar.gui.views.support import build_support_view

        view = build_support_view(ft.UrlLauncher())
        assert view.expand is True

    def test_uses_shared_page_shell(self):
        from motorsport_calendar.gui.views.support import build_support_view

        view = build_support_view(ft.UrlLauncher())
        assert view.content.width == theme.MAX_CONTENT_WIDTH

    def test_header_uses_nav_support_title_and_icon(self):
        from motorsport_calendar.gui.strings import STRINGS
        from motorsport_calendar.gui.views.support import build_support_view

        view = build_support_view(ft.UrlLauncher())
        column = view.content.content
        header = column.controls[0]
        icon_row = header.controls[0]
        icon = next(c for c in icon_row.controls if isinstance(c, ft.Icon))
        assert icon.icon == ft.Icons.VOLUNTEER_ACTIVISM
        texts = _collect_all_text(view)
        assert STRINGS.nav_support in texts

    def test_shows_the_donate_section_with_both_placeholders(self):
        from motorsport_calendar.gui.strings import STRINGS
        from motorsport_calendar.gui.views.support import build_support_view

        view = build_support_view(ft.UrlLauncher())
        texts = _collect_all_text(view)
        assert STRINGS.support_section_donate in texts
        assert STRINGS.support_paypal_label in texts
        assert STRINGS.support_github_sponsors_label in texts
        # Both are "coming soon" — no real link exists yet (brief: "aucun
        # lien réel n'est encore nécessaire").
        assert texts.count(STRINGS.prefs_coming_soon) == 2

    def test_donate_placeholders_are_not_clickable(self):
        """No real PayPal/GitHub Sponsors URL exists yet — the brief
        explicitly says none is needed, so these must stay inert."""
        from motorsport_calendar.gui.views.support import build_support_view

        view = build_support_view(ft.UrlLauncher())
        column = view.content.content
        donate_section = column.controls[2]
        for control in _flatten_controls(donate_section):
            assert getattr(control, "on_click", None) is None

    def test_shows_the_roadmap_section_with_every_idea(self):
        """ "Voter pour les prochaines fonctionnalités" — présentation
        uniquement, aucun système de vote local."""
        from motorsport_calendar.gui.strings import STRINGS
        from motorsport_calendar.gui.views.support import build_support_view

        view = build_support_view(ft.UrlLauncher())
        texts = _collect_all_text(view)
        assert STRINGS.support_section_roadmap in texts
        for idea in STRINGS.support_roadmap_ideas:
            assert idea in texts

    def test_roadmap_ideas_are_not_clickable(self):
        """A presentation only — clicking an idea must do nothing, there
        is no local vote system."""
        from motorsport_calendar.gui.views.support import build_support_view

        view = build_support_view(ft.UrlLauncher())
        column = view.content.content
        roadmap_section = column.controls[3]
        for control in _flatten_controls(roadmap_section):
            assert getattr(control, "on_click", None) is None

    def test_shows_the_suggestions_section_with_a_button(self):
        """``ft.Button``'s ``content`` here is a plain string (not a
        nested ``ft.Text``), so it's invisible to ``_collect_all_text``
        — check the button control itself, same fix as Sprint 53's
        "Voir la version" button test."""
        from motorsport_calendar.gui.strings import STRINGS
        from motorsport_calendar.gui.views.support import build_support_view

        view = build_support_view(ft.UrlLauncher())
        texts = _collect_all_text(view)
        assert STRINGS.support_section_suggestions in texts
        buttons = [c for c in _flatten_controls(view) if isinstance(c, ft.Button)]
        assert any(b.content == STRINGS.support_suggestions_btn for b in buttons)

    def test_suggestions_button_opens_github_discussions(self):
        from unittest.mock import patch

        from motorsport_calendar.gui.views.support import (
            _GITHUB_DISCUSSIONS_URL,
            build_support_view,
        )

        launcher = ft.UrlLauncher()
        with patch("motorsport_calendar.gui.views.support.make_url_opener") as mock_make_opener:
            build_support_view(launcher)
        mock_make_opener.assert_any_call(launcher, _GITHUB_DISCUSSIONS_URL)

    def test_shows_the_report_section_with_a_button(self):
        from motorsport_calendar.gui.strings import STRINGS
        from motorsport_calendar.gui.views.support import build_support_view

        view = build_support_view(ft.UrlLauncher())
        texts = _collect_all_text(view)
        assert STRINGS.support_section_report in texts
        buttons = [c for c in _flatten_controls(view) if isinstance(c, ft.Button)]
        assert any(b.content == STRINGS.support_report_btn for b in buttons)

    def test_report_button_opens_github_issues(self):
        from unittest.mock import patch

        from motorsport_calendar.gui.views.support import (
            _GITHUB_ISSUES_URL,
            build_support_view,
        )

        launcher = ft.UrlLauncher()
        with patch("motorsport_calendar.gui.views.support.make_url_opener") as mock_make_opener:
            build_support_view(launcher)
        mock_make_opener.assert_any_call(launcher, _GITHUB_ISSUES_URL)

    def test_discussions_and_issues_urls_are_both_github_urls_and_distinct(self):
        from motorsport_calendar.gui.views.support import (
            _GITHUB_DISCUSSIONS_URL,
            _GITHUB_ISSUES_URL,
        )

        assert _GITHUB_DISCUSSIONS_URL.startswith("https://github.com/")
        assert _GITHUB_ISSUES_URL.startswith("https://github.com/")
        assert _GITHUB_DISCUSSIONS_URL != _GITHUB_ISSUES_URL

    def test_all_four_sections_present(self):
        from motorsport_calendar.gui.strings import STRINGS
        from motorsport_calendar.gui.views.support import build_support_view

        view = build_support_view(ft.UrlLauncher())
        texts = _collect_all_text(view)
        for header in (
            STRINGS.support_section_donate,
            STRINGS.support_section_roadmap,
            STRINGS.support_section_suggestions,
            STRINGS.support_section_report,
        ):
            assert header in texts


class TestAllViewsShareTheSameGrid:
    """Sprint 27 — every page must use the exact same layout grid."""

    def _all_views(self):
        from motorsport_calendar.gui.views.about import build_about_view
        from motorsport_calendar.gui.views.calendar import CalendarViewControls, build_calendar_view
        from motorsport_calendar.gui.views.favorites import build_favorites_view
        from motorsport_calendar.gui.views.preferences import (
            PreferencesViewControls,
            build_preferences_view,
        )
        from motorsport_calendar.gui.views.search import build_search_view
        from motorsport_calendar.gui.views.support import build_support_view
        from motorsport_calendar.gui.views.weekend import build_weekend_view

        calendar_controls = CalendarViewControls(
            year_dropdown=ft.Dropdown(label="Saison", value="2026"),
            refresh_btn=ft.IconButton(icon=ft.Icons.REFRESH),
            output_field=ft.TextField(label="Fichier"),
            browse_btn=ft.IconButton(icon=ft.Icons.FOLDER_OPEN),
            generate_btn=ft.Button(content="Créer"),
            progress_ring=ft.ProgressRing(width=22, height=22, visible=False),
            error_text=ft.Text(value=""),
        )
        preferences_controls = PreferencesViewControls(
            update_check_enabled_switch=ft.Switch(value=True),
            default_year_dropdown=ft.Dropdown(value="current"),
            ics_alarm_minutes_dropdown=ft.Dropdown(value="30"),
        )
        return [
            build_weekend_view(),
            build_calendar_view(calendar_controls),
            build_search_view(ft.TextField(), SearchResults(), False),
            build_favorites_view([], 0, lambda cid: None, lambda c, e: None),
            build_preferences_view(preferences_controls),
            build_about_view(ft.UrlLauncher()),
            build_support_view(ft.UrlLauncher()),
        ]

    def test_every_view_is_a_container_expanding_to_fill(self):
        for view in self._all_views():
            assert isinstance(view, ft.Container)
            assert view.expand is True

    def test_every_view_shares_the_same_max_content_width(self):
        widths = {view.content.width for view in self._all_views()}
        assert widths == {theme.MAX_CONTENT_WIDTH}

    def test_every_view_centers_horizontally_not_its_content(self):
        for view in self._all_views():
            assert view.alignment == ft.Alignment.TOP_CENTER

    def test_every_view_left_aligns_its_content_column(self):
        for view in self._all_views():
            column = view.content.content
            assert column.horizontal_alignment == ft.CrossAxisAlignment.STRETCH

    def test_every_view_uses_the_same_outer_padding(self):
        expected = theme.page_padding()
        for view in self._all_views():
            assert view.padding == expected
