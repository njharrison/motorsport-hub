"""PageHeader — the one page-title component every view uses.

Bundles icon + title + optional subtitle + the trailing separator into a
single control, so no view builds its own ``theme.section_title() +
ft.Divider()`` pair again. Every page that shows a header uses exactly
this component — one visual identity for "this is the top of a page",
everywhere, today and in every future screen.

Sprint 43: optional ``trailing`` slot, added for "Mon calendrier"'s season
selector — demoted to a secondary, top-right control instead of the page's
main element. Defaults to ``None``, so every other page's header is
byte-for-byte unchanged (this was the deciding factor over building a
one-off title row inside calendar.py: one component, one visual identity,
still true after this sprint).
"""

from __future__ import annotations

import flet as ft

from motorsport_calendar.gui import theme


def PageHeader(
    title: str,
    *,
    icon: ft.IconData | None = None,
    subtitle: str | None = None,
    trailing: ft.Control | None = None,
) -> ft.Control:
    """Return the page header block: icon + title, optional subtitle, divider.

    Args:
        title: the page's own name (e.g. "Ce week-end", "Préférences") —
            typically the same label shown in the navigation rail.
        icon: optional leading icon, matching the page's nav destination.
        subtitle: optional secondary line under the title (e.g. a date
            range) — always plain, muted text; no further styling knobs.
        trailing: optional control shown at the top-right of the title row
            (e.g. a secondary selector) — never affects the divider/
            subtitle below it.
    """
    title_row: ft.Control = theme.section_title(title, icon=icon)
    if trailing is not None:
        title_row = ft.Row(
            [title_row, trailing],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

    rows: list[ft.Control] = [title_row]
    if subtitle is not None:
        rows.append(ft.Text(subtitle, size=theme.FontSize.SMALL, color=theme.Colors.TEXT_MUTED))
    rows.append(ft.Divider(height=theme.Spacing.MD))
    return ft.Column(rows, spacing=theme.Spacing.XXS)
