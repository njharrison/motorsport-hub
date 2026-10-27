"""⭐ Mes favoris — manage favorite championships (Sprint 44).

Replaces the Sprint 31 placeholder with a real page: every registered
championship, grouped by category, each a selectable "button" — exactly
the same UI as "Mon calendrier"'s championship picker (Sprint 43), reused
as-is via ``gui/components/championship_selector.py`` rather than
rebuilt, per the sprint brief's "ne pas dupliquer le code de sélection des
championnats". Here "selected" means "favorited", not "picked for this
generation" — the component itself is indifferent to which.

No business logic here: main_view.py resolves ``categories.get_groups_for``/
``display_names.get_display_name`` and ``FavoritesService`` into
``ChampionshipCategoryData`` (exactly as it already does for "Mon
calendrier"), this module only renders it.

Sprint 54 (Beta UX recette): header icon switched from ``STAR_BORDER`` to
``STAR`` — the nav rail already uses ``STAR`` as this page's *selected*
icon (``STAR_OUTLINE`` unselected), so the header showing a third,
different star glyph (``STAR_BORDER``) was an unintended inconsistency,
not a deliberate third state. Visual-only, no layout change.
"""

from __future__ import annotations

from collections.abc import Callable

import flet as ft

from motorsport_calendar.gui.components.championship_selector import (
    ChampionshipCategoryData,
    build_championship_selector,
)
from motorsport_calendar.gui.components.layout import PageContainer, PageHeader
from motorsport_calendar.gui.strings import STRINGS, plural


def build_favorites_view(
    category_groups: list[ChampionshipCategoryData],
    favorite_count: int,
    on_favorite_click: Callable[[str], None],
    on_category_toggle: Callable[[str, bool], None],
) -> ft.Control:
    """Return the "Mes favoris" page, through the Layout System.

    Args:
        category_groups: every registered championship, grouped by
            category — ``selected`` means "favorited" (main_view.py owns
            ``FavoritesService``, this module never reads it directly).
        favorite_count: ``len(FavoritesService().list())`` — shown as the
            page's subtitle (``PageHeader``'s existing slot, no new
            component).
        on_favorite_click: called with a championship id when its button
            is clicked — toggles favorite status (main_view.py's job).
        on_category_toggle: called when a category accordion is
            expanded/collapsed.
    """
    subtitle = STRINGS.favorites_count.format(n=favorite_count, s=plural(favorite_count))
    return PageContainer(
        header=PageHeader(STRINGS.nav_favorites, icon=ft.Icons.STAR, subtitle=subtitle),
        body=[build_championship_selector(category_groups, on_favorite_click, on_category_toggle)],
    )
