"""EmptyState — the one "nothing here yet" pattern for the whole app.

Favoris, Ce week-end (no race this weekend), and every future empty screen
(Notifications, Historique, Recherche with no results, ...) share this
exact layout: optional icon, title, optional message — always presented in
a card, so an empty page never reads as broken or unfinished (the rule
introduced ad hoc in Sprint 28, now centralized here instead of hand-rolled
per view).
"""

from __future__ import annotations

import flet as ft

from motorsport_calendar.gui import theme


def EmptyState(
    title: str,
    *,
    message: str | None = None,
    icon: ft.IconData | None = None,
) -> ft.Control:
    """Return a card-wrapped empty-state block.

    Args:
        title: the main message — a short label, never a full sentence
            (e.g. "Aucune course ce week-end", no trailing period; see
            ``strings.py``'s own Sprint 54 note on this convention).
        message: optional secondary line (e.g. a hint, or "coming soon").
        icon: optional icon shown above the title.
    """
    controls: list[ft.Control] = []
    if icon is not None:
        controls.append(ft.Icon(icon, size=theme.IconSize.LG, color=theme.Colors.TEXT_MUTED))
    controls.append(
        ft.Text(
            title,
            size=theme.FontSize.HEADLINE,
            weight=ft.FontWeight.BOLD,
            color=theme.Colors.TEXT_SECONDARY,
        )
    )
    if message is not None:
        controls.append(ft.Text(message, size=theme.FontSize.BODY, color=theme.Colors.TEXT_GHOST))
    return theme.card(ft.Column(controls, spacing=theme.Spacing.XS))
