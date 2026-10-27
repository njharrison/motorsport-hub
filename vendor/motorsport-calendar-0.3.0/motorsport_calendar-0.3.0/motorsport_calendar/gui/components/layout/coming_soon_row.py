"""ComingSoonRow — the one "prepared, not yet real" row shape.

Promoted here (Sprint 57) once a 2nd real consumer needed the exact same
shape ``views/preferences.py``'s own ``_pref_row`` already had since
Sprint 52 (icon + label + a muted "Disponible prochainement" chip, in a
bordered card) — "Soutenir le projet"'s PayPal/GitHub Sponsors slots are
prepared exactly the same way: a labeled place-holder, no real link yet.
Same "mutualize on the second real use" principle already applied
throughout this project (providers, ChampionshipCard,
championship_selector, ``url_opener.make_url_opener``).
"""

from __future__ import annotations

import flet as ft

from motorsport_calendar.gui import theme
from motorsport_calendar.gui.strings import STRINGS


def ComingSoonRow(icon: ft.IconData, label: str) -> ft.Control:
    """Return a bordered card: icon, label, and a "Disponible
    prochainement" chip — for any setting/link that is prepared but not
    yet wired to something real."""
    return theme.card(
        ft.Row(
            controls=[
                ft.Icon(icon, size=theme.IconSize.MD, color=theme.Colors.TEXT_MUTED),
                ft.Text(
                    label,
                    size=theme.FontSize.BODY,
                    color=theme.Colors.TEXT_SECONDARY,
                    expand=True,
                ),
                theme.chip(STRINGS.prefs_coming_soon),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=theme.Spacing.SM,
        )
    )
