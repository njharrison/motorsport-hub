"""📊 Tableau de bord — the app's real home page (Sprint 39, Sprint 53).

Renders one of exactly 2 states, driven by main_view.py:
  - loading : ``build_dashboard_view(None)``               — "Chargement..."
  - loaded  : ``build_dashboard_view(DashboardData(...))``  — stats + sections

Pure layout — fetching and aggregating stats lives in
``controller.get_dashboard_data`` / ``gui/dashboard.py``. Every state is
composed from the Layout System (``PageContainer``/``PageHeader``/
``Section``/``SectionHeader``/``CardList``/``EmptyState``) plus the
existing ``ChampionshipCard`` component reused as-is for consistency with
"Ce week-end" — this view builds no container, padding, header, or card
layout of its own, and introduces no new Design System tokens (only
``theme.card``/``theme.chip``/``theme.Spacing``/``theme.FontSize``/
``theme.Colors``, exactly like every other view).

Sprint 53 adds 3 sections, all pure layout over data main_view.py already
resolved (no business logic here, per the sprint brief):
  - "Nouveautés" — renders ``DashboardData.update`` (Sprint 51's
    ``UpdateCheckResult``, unchanged); entirely omitted (not even a
    header) when there is nothing to show, exactly as the brief specifies.
  - "Accès rapides" — 4 navigation cards; clicking one calls
    ``on_navigate`` with a string key, main_view.py owns what that key
    means (which nav index it maps to) — this module never touches
    ``nav_rail``/``content_area``.
  - "État de Motorsport Calendar" — reuses ``_stat_card`` (Sprint 39)
    as-is, no new stat-display primitive introduced.

Sprint 54 (Beta UX recette): ``_HEADER_ICON`` switched from the outlined
to the filled ``SPACE_DASHBOARD`` glyph — every other page's header icon
already matched its nav rail's *selected* (filled) variant
(``weekend.py``/``calendar.py``/``search.py``/``favorites.py``/
``preferences.py``); the Dashboard was the one page still showing the
outlined glyph in its own header. Visual-only, no layout change.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING

import flet as ft

from motorsport_calendar.gui import theme
from motorsport_calendar.gui.components.layout import (
    EmptyState,
    PageContainer,
    PageHeader,
    Section,
    SectionHeader,
)
from motorsport_calendar.gui.strings import STRINGS

if TYPE_CHECKING:
    from motorsport_calendar.gui.dashboard import DashboardData

_HEADER_ICON = ft.Icons.SPACE_DASHBOARD

# "Accès rapides" destinations — the string key main_view.py's on_navigate
# receives; main_view.py alone decides which nav index each maps to (see
# its own _navigate_to). Icons match the corresponding NavigationRailDestination
# in main_view.py, so a quick-access card visually echoes its nav entry.
_QUICK_ACCESS_ITEMS: tuple[tuple[str, ft.IconData, str], ...] = (
    ("weekend", ft.Icons.SPORTS_MOTORSPORTS_OUTLINED, STRINGS.nav_weekend),
    ("calendar", ft.Icons.CALENDAR_MONTH_OUTLINED, STRINGS.nav_my_calendar),
    ("search", ft.Icons.SEARCH_OUTLINED, STRINGS.nav_search),
    ("favorites", ft.Icons.STAR_OUTLINE, STRINGS.nav_favorites),
)


def _loading_state() -> ft.Control:
    loading_card = theme.card(
        ft.Row(
            [
                ft.ProgressRing(width=16, height=16),
                ft.Text(
                    STRINGS.weekend_loading,
                    size=theme.FontSize.BODY,
                    color=theme.Colors.TEXT_SECONDARY,
                ),
            ],
            spacing=theme.Spacing.SM,
        )
    )
    return PageContainer(
        header=PageHeader(STRINGS.nav_dashboard, icon=_HEADER_ICON),
        body=[Section(loading_card)],
    )


def _stat_card(label: str, value: str) -> ft.Control:
    """One glanceable "big number + label" block — a metric, not a card of
    detailed content (that's what ChampionshipCard is for).
    """
    return theme.card(
        ft.Column(
            [
                ft.Text(
                    value,
                    size=theme.FontSize.DISPLAY,
                    weight=ft.FontWeight.BOLD,
                    color=theme.Colors.PRIMARY,
                ),
                ft.Text(label, size=theme.FontSize.SMALL, color=theme.Colors.TEXT_MUTED),
            ],
            spacing=theme.Spacing.XXS,
        ),
        width=200,
    )


def _stats_row(data: DashboardData) -> ft.Control:
    if data.weekend.found:
        weekend_value = f"{data.weekend.friday:%d/%m} - {data.weekend.sunday:%d/%m}"
    else:
        weekend_value = STRINGS.dashboard_next_weekend_none

    return ft.Row(
        [
            _stat_card(STRINGS.dashboard_stat_next_weekend, weekend_value),
            _stat_card(STRINGS.dashboard_stat_championships, str(data.total_championships)),
            _stat_card(STRINGS.dashboard_stat_events, str(data.total_events_season)),
            _stat_card(STRINGS.dashboard_stat_sessions, str(data.total_sessions_season)),
        ],
        spacing=theme.Spacing.SM,
        wrap=True,
    )


def _weekend_championships_section(data: DashboardData) -> ft.Control:
    header = SectionHeader(STRINGS.dashboard_section_weekend_championships)
    if not data.weekend.found or not data.weekend.cards:
        return Section(header, EmptyState(STRINGS.dashboard_weekend_championships_empty))

    chips = ft.Row(
        [theme.chip(card.championship_name) for card in data.weekend.cards],
        spacing=theme.Spacing.XXS,
        wrap=True,
    )
    return Section(header, chips)


def _next_race_section(data: DashboardData) -> ft.Control:
    header = SectionHeader(STRINGS.dashboard_section_next_race)
    if data.next_race is None:
        return Section(header, EmptyState(STRINGS.dashboard_next_race_empty))

    content = theme.card(
        ft.Row(
            [
                ft.Text(
                    data.next_race.championship_name,
                    size=theme.FontSize.LABEL,
                    weight=ft.FontWeight.W_600,
                ),
                ft.Text(
                    data.next_race.display,
                    size=theme.FontSize.SUBTITLE,
                    weight=ft.FontWeight.BOLD,
                    color=theme.Colors.PRIMARY,
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
    )
    return Section(header, content)


def _news_section(
    data: DashboardData,
    on_view_release: Callable[[ft.ControlEvent], Awaitable[None]] | None,
) -> ft.Control | None:
    """ "Nouveautés" — Sprint 53 brief, verbatim: no update available means
    *nothing* is rendered, not even a header (unlike every other section
    here, which always shows at least an EmptyState)."""
    update = data.update
    if update is None or not update.update_available or update.manifest is None:
        return None

    manifest = update.manifest
    card = theme.card(
        ft.Column(
            [
                ft.Row(
                    [
                        ft.Text(
                            STRINGS.update_new_version,
                            size=theme.FontSize.SMALL,
                            color=theme.Colors.TEXT_SECONDARY,
                        ),
                        ft.Text(
                            manifest.version,
                            size=theme.FontSize.SMALL,
                            weight=ft.FontWeight.BOLD,
                            color=theme.Colors.PRIMARY,
                        ),
                    ],
                    spacing=theme.Spacing.XXS,
                ),
                ft.Text(
                    manifest.summary,
                    size=theme.FontSize.SMALL,
                    color=theme.Colors.TEXT_SECONDARY,
                ),
                ft.Button(
                    content=STRINGS.update_view_btn,
                    icon=ft.Icons.OPEN_IN_NEW,
                    on_click=on_view_release,
                ),
            ],
            spacing=theme.Spacing.XS,
        )
    )
    return Section(SectionHeader(STRINGS.dashboard_section_news), card)


def _quick_access_section(on_navigate: Callable[[str], None] | None) -> ft.Control:
    def _card(key: str, icon: ft.IconData, label: str) -> ft.Control:
        control = theme.card(
            ft.Column(
                [
                    ft.Icon(icon, size=theme.IconSize.LG, color=theme.Colors.PRIMARY),
                    ft.Text(
                        label,
                        size=theme.FontSize.LABEL,
                        weight=ft.FontWeight.W_600,
                        color=theme.Colors.TEXT_PRIMARY,
                    ),
                ],
                spacing=theme.Spacing.XXS,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            width=140,
        )
        if on_navigate is not None:
            control.on_click = lambda e, k=key: on_navigate(k)
        return control

    cards = ft.Row(
        [_card(key, icon, label) for key, icon, label in _QUICK_ACCESS_ITEMS],
        spacing=theme.Spacing.SM,
        wrap=True,
    )
    return Section(SectionHeader(STRINGS.dashboard_section_quick_access), cards)


def _status_section(data: DashboardData) -> ft.Control:
    stats = ft.Row(
        [
            _stat_card(STRINGS.dashboard_stat_version, data.current_version),
            _stat_card(STRINGS.dashboard_stat_active_championships, str(data.active_championships)),
            _stat_card(STRINGS.dashboard_stat_functional_providers, str(data.functional_providers)),
            _stat_card(STRINGS.dashboard_stat_favorites, str(data.favorite_count)),
        ],
        spacing=theme.Spacing.SM,
        wrap=True,
    )
    return Section(SectionHeader(STRINGS.dashboard_section_status), stats)


def _loaded_state(
    data: DashboardData,
    on_navigate: Callable[[str], None] | None,
    on_view_release: Callable[[ft.ControlEvent], Awaitable[None]] | None,
    on_refresh: Callable[[ft.ControlEvent], Awaitable[None]] | None,
) -> ft.Control:
    body: list[ft.Control] = [Section(_stats_row(data))]

    news = _news_section(data, on_view_release)
    if news is not None:
        body.append(news)

    body.append(_quick_access_section(on_navigate))
    body.append(_weekend_championships_section(data))
    body.append(_next_race_section(data))
    body.append(_status_section(data))

    trailing = None
    if on_refresh is not None:
        trailing = ft.IconButton(
            icon=ft.Icons.REFRESH, tooltip=STRINGS.refresh_tooltip, on_click=on_refresh
        )
    return PageContainer(
        header=PageHeader(STRINGS.nav_dashboard, icon=_HEADER_ICON, trailing=trailing),
        body=body,
    )


def build_dashboard_view(
    data: DashboardData | None = None,
    *,
    on_navigate: Callable[[str], None] | None = None,
    on_view_release: Callable[[ft.ControlEvent], Awaitable[None]] | None = None,
    on_refresh: Callable[[ft.ControlEvent], Awaitable[None]] | None = None,
) -> ft.Control:
    """Return the Dashboard view for exactly one of the 2 states.

    Args:
        data: ``None`` while the fetch is in flight (loading state),
            otherwise the outcome of ``controller.get_dashboard_data``.
        on_navigate: called with one of ``"weekend"``/``"calendar"``/
            ``"search"``/``"favorites"`` when a "Accès rapides" card is
            clicked — main_view.py alone knows what to do with it
            (Sprint 53). Ignored in the loading state.
        on_view_release: called when the "Nouveautés" card's "Voir la
            version" button is clicked — the exact same handler
            main_view.py's Sprint 51 startup dialog already uses (never a
            second implementation of "open this URL"). Ignored in the
            loading state, and whenever there is no update to show.
        on_refresh: called when the manual-refresh button is clicked
            (MC-002 P0-7) — main_view.py alone knows how to re-fetch. No
            refresh button in the loading state (nothing to refresh yet);
            ``None`` renders no button either.
    """
    if data is None:
        return _loading_state()
    return _loaded_state(data, on_navigate, on_view_release, on_refresh)
