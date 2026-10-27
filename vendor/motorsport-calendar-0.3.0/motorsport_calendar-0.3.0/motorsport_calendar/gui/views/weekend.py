"""🏁 Ce week-end — version fonctionnelle (Sprint 29), Layout System (Sprint 31).

Renders one of exactly 3 states, driven by main_view.py:
  - loading  : ``build_weekend_view(None)``            — "Chargement..."
  - empty    : ``build_weekend_view(WeekendResult(found=False, ...))``
  - found    : ``build_weekend_view(WeekendResult(found=True, ...))``

Pure layout — fetching and finding the next race weekend lives in
``controller.get_upcoming_weekend`` / ``upcoming_weekend.py``. Every state
is composed from the Layout System (``PageContainer``/``PageHeader``/
``Section``/``CardList``/``EmptyState``) — this view builds no container,
padding, header, or card layout of its own.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import flet as ft

from motorsport_calendar.gui import theme
from motorsport_calendar.gui.components.championship_card import build_championship_card
from motorsport_calendar.gui.components.layout import (
    CardList,
    EmptyState,
    PageContainer,
    PageHeader,
    Section,
)
from motorsport_calendar.gui.strings import STRINGS

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from motorsport_calendar.gui.upcoming_weekend import WeekendResult

_HEADER_ICON = ft.Icons.SPORTS_MOTORSPORTS


def _refresh_button(
    on_refresh: Callable[[ft.ControlEvent], Awaitable[None]] | None,
) -> ft.Control | None:
    """MC-002 (P0-7) — the one manual-refresh action shared by every
    non-loading state; ``None`` renders nothing (loading state, or a
    caller that hasn't wired refresh yet), same optional-trailing
    convention as ``PageHeader`` itself."""
    if on_refresh is None:
        return None
    return ft.IconButton(
        icon=ft.Icons.REFRESH, tooltip=STRINGS.refresh_tooltip, on_click=on_refresh
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
        header=PageHeader(STRINGS.nav_weekend, icon=_HEADER_ICON),
        body=[Section(loading_card)],
    )


def _empty_state(
    result: WeekendResult, on_refresh: Callable[[ft.ControlEvent], Awaitable[None]] | None
) -> ft.Control:
    message = None
    if result.next_hint_date is not None:
        message = STRINGS.weekend_next_hint.format(date=f"{result.next_hint_date:%d/%m}")
    return PageContainer(
        header=PageHeader(
            STRINGS.nav_weekend, icon=_HEADER_ICON, trailing=_refresh_button(on_refresh)
        ),
        body=[Section(EmptyState(STRINGS.weekend_empty_title, message=message))],
    )


def _found_state(
    result: WeekendResult, on_refresh: Callable[[ft.ControlEvent], Awaitable[None]] | None
) -> ft.Control:
    subtitle = f"{result.friday:%d/%m} - {result.sunday:%d/%m}"
    cards = [build_championship_card(card) for card in result.cards]
    return PageContainer(
        header=PageHeader(
            STRINGS.nav_weekend,
            icon=_HEADER_ICON,
            subtitle=subtitle,
            trailing=_refresh_button(on_refresh),
        ),
        body=[Section(CardList(cards))],
    )


def build_weekend_view(
    result: WeekendResult | None = None,
    *,
    on_refresh: Callable[[ft.ControlEvent], Awaitable[None]] | None = None,
) -> ft.Control:
    """Return the Ce week-end view for exactly one of the 3 states.

    Args:
        result: ``None`` while the fetch is in flight (loading state),
            otherwise the outcome of ``controller.get_upcoming_weekend``.
        on_refresh: called when the manual-refresh button is clicked
            (MC-002 P0-7) — main_view.py alone knows how to re-fetch.
            No refresh button in the loading state (nothing to refresh
            yet); ``None`` elsewhere renders no button either.
    """
    if result is None:
        return _loading_state()
    if not result.found:
        return _empty_state(result, on_refresh)
    return _found_state(result, on_refresh)
