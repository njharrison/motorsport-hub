"""Section / SectionHeader — grouping and sub-headings within a page body.

``Section`` owns the gap *between* related blocks — no view should
hand-roll an ``ft.Container(height=...)`` spacer between two blocks again;
wrap them in a ``Section`` instead. ``SectionHeader`` is a distinct,
smaller heading used *inside* a Section (e.g. to label one of several
card groups on a future Recherche/Tableau de bord page) — it is not a
substitute for ``PageHeader``, which owns the page's own title.
"""

from __future__ import annotations

import flet as ft

from motorsport_calendar.gui import theme


def Section(*controls: ft.Control, spacing: int = theme.Spacing.SM) -> ft.Control:
    """Group related blocks with the app's one standard inter-block gap."""
    return ft.Column(list(controls), spacing=spacing)


def SectionHeader(title: str, *, icon: ft.IconData | None = None) -> ft.Control:
    """A smaller heading for a sub-section within a page's body.

    Distinct from ``PageHeader``: no divider, no page-level weight — just
    a muted label, for grouping content within a ``Section`` (e.g.
    labelling one of several card groups on a future dashboard).
    """
    controls: list[ft.Control] = []
    if icon is not None:
        controls.append(ft.Icon(icon, size=theme.IconSize.SM, color=theme.Colors.TEXT_MUTED))
    controls.append(
        ft.Text(
            title,
            size=theme.FontSize.SMALL,
            weight=ft.FontWeight.W_600,
            color=theme.Colors.TEXT_MUTED,
        )
    )
    return ft.Row(controls, spacing=theme.Spacing.XXS)
