"""CardList — the one reusable vertical list of cards.

Uniform vertical spacing for a list of cards — the layout concern only.
A future separator between items is a natural extension point if a list
ever needs one, but nothing builds it today: no current caller needs it,
and an unused option is dead weight, not readiness.

Used today by Ce week-end (one ChampionshipCard per event); tomorrow by
Favoris, Recherche, Tableau de bord, Notifications, Historique — any page
showing a list of cards.
"""

from __future__ import annotations

from collections.abc import Sequence

import flet as ft

from motorsport_calendar.gui import theme


def CardList(cards: Sequence[ft.Control], *, spacing: int = theme.Spacing.SM) -> ft.Control:
    """Return *cards* stacked with the app's one standard card-list gap."""
    return ft.Column(list(cards), spacing=spacing)
