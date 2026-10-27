"""ChampionshipSelector — accordion-of-selectable-buttons, shared by "Mon
calendrier" and "Mes favoris" (Sprint 44).

Extracted from ``gui/views/calendar.py`` (Sprint 43, which introduced this
exact UI — championships grouped by category in single-level accordions,
each championship a selectable "button" rather than a checkbox) once a
second real consumer appeared: "Mes favoris" (Sprint 44) needed the
identical interaction (pick championships from the same grouped list,
multi-select, never radio buttons), just wired to a different meaning
("favorited" instead of "selected for this generation"). Promoting it here
avoids a second, drifting implementation of the same selection UI — the
sprint brief's own "ne pas dupliquer le code de sélection des
championnats", applied the same way providers were mutualized on their own
second real use (Sprint 35, ADR-026) and controller fetch pipelines were
(Sprints 39-40).

The component knows only its own display-ready models
(``ChampionshipButtonData``/``ChampionshipCategoryData``) — never a
``GenerateState``, never ``FavoritesService``, never why a championship is
"selected". Callers (``gui/main_view.py``, for both "Mon calendrier" and
"Mes favoris") decide what "selected" means and own the actual state.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import flet as ft

from motorsport_calendar.gui import theme
from motorsport_calendar.gui.components.layout import Section


@dataclass(frozen=True)
class ChampionshipButtonData:
    """One selectable championship "button" — pure display data.

    ``selected`` drives ``theme.card(..., selected=...)``'s existing
    highlighted style (border + tinted surface) — anticipated since
    Sprint 26/30, first put to use in Sprint 43.
    """

    championship_id: str
    display_name: str
    selected: bool


@dataclass(frozen=True)
class ChampionshipCategoryData:
    """One accordion section — pure display data.

    ``category_id`` is the stable key a caller uses to remember whether
    the user expanded/collapsed this category across rebuilds — never
    rendered itself; ``label`` (already formatted, e.g. "🏎  Formula") is
    what's shown.
    """

    category_id: str
    label: str
    expanded: bool
    options: tuple[ChampionshipButtonData, ...]


def _championship_button(
    option: ChampionshipButtonData, on_click: Callable[[str], None]
) -> ft.Control:
    """One selectable championship "button" — flows in a wrapped row
    inside each category's accordion. Multi-select stays possible (never
    radio buttons): clicking toggles this one championship only.
    """
    btn = theme.card(
        ft.Text(
            option.display_name,
            size=theme.FontSize.BODY,
            weight=ft.FontWeight.W_600 if option.selected else ft.FontWeight.NORMAL,
            color=theme.Colors.TEXT_PRIMARY if option.selected else theme.Colors.TEXT_SECONDARY,
        ),
        selected=option.selected,
    )
    btn.on_click = lambda e: on_click(option.championship_id)
    return btn


def _category_accordion(
    group: ChampionshipCategoryData,
    on_championship_click: Callable[[str], None],
    on_category_toggle: Callable[[str, bool], None],
) -> ft.Control:
    """One category as a single-level accordion (``ft.ExpansionTile``) —
    never nested. Expand state is remembered by the caller
    (``group.expanded``) and restored here on every rebuild, so toggling a
    championship inside "Endurance" never collapses it back.
    """

    def _on_change(e: ft.ControlEvent) -> None:
        on_category_toggle(group.category_id, e.control.expanded)

    return ft.ExpansionTile(
        title=ft.Text(group.label, size=theme.FontSize.LABEL, weight=ft.FontWeight.W_600),
        controls=[
            ft.Container(
                content=ft.Row(
                    [_championship_button(opt, on_championship_click) for opt in group.options],
                    spacing=theme.Spacing.XS,
                    wrap=True,
                ),
                padding=ft.Padding.only(
                    left=theme.Spacing.XS, bottom=theme.Spacing.SM, right=theme.Spacing.XS
                ),
            )
        ],
        expanded=group.expanded,
        on_change=_on_change,
    )


def build_championship_selector(
    groups: list[ChampionshipCategoryData],
    on_championship_click: Callable[[str], None],
    on_category_toggle: Callable[[str, bool], None],
) -> ft.Control:
    """One accordion per category, in the order provided
    (``categories.get_groups_for``, unchanged) — the shared "pick some
    championships" UI used by both "Mon calendrier" (Sprint 43) and "Mes
    favoris" (Sprint 44).
    """
    return Section(
        *[_category_accordion(g, on_championship_click, on_category_toggle) for g in groups]
    )
