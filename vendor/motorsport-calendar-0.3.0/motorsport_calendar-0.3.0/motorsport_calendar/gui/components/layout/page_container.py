"""PageContainer — the single page shell every view renders through.

Owns exactly one responsibility: max width, horizontal/vertical padding,
and overall alignment. A view never builds its own Container/padding/width
again — it hands PageContainer a header and a body, nothing more.

Internally this is ``theme.page_shell`` wearing a header/body-shaped API
instead of a flat ``*sections`` list, so every call site reads
declaratively instead of repeating the same Container/Column boilerplate:

    return PageContainer(
        header=PageHeader("Ce week-end", icon=ft.Icons.SPORTS_MOTORSPORTS),
        body=[Section(CardList(cards))],
    )

No new Design System tokens: this module only calls into ``theme.py``,
never redefines spacing/color/width values of its own.

Sprint 43: optional ``footer`` slot, added for "Mon calendrier"'s "Créer
mon calendrier" action row, which must stay visible without scrolling the
whole page. When omitted (every view except Mon calendrier), behaves
exactly as before — header + body scroll together as a single column via
``theme.page_shell``. When given, only header + body scroll (in their own
bounded region); footer is pinned below, never inside the scrolling area.
Still the exact same width/padding/alignment/spacing tokens as
``theme.page_shell`` — this is a structural split, not a new visual style.
"""

from __future__ import annotations

from collections.abc import Sequence

import flet as ft

from motorsport_calendar.gui import theme


def PageContainer(
    *,
    header: ft.Control | None = None,
    body: Sequence[ft.Control] = (),
    footer: ft.Control | None = None,
) -> ft.Control:
    """Return the full page shell: header (if any), then body, then footer.

    Args:
        header: the page's ``PageHeader``, or ``None`` for the rare page
            that renders its own title inline instead of the standard
            header (e.g. À propos's compact branding block).
        body: the page's content — already composed from ``Section``,
            ``CardList``, ``EmptyState``, or plain controls. Passed
            through untouched; this function adds no spacing logic of its
            own beyond what ``theme.page_shell`` already provides between
            top-level blocks.
        footer: optional fixed content pinned below the scrollable
            header+body — e.g. a primary action that must always stay
            visible. ``None`` (every view but Mon calendrier) keeps the
            original single-scroll behavior untouched.
    """
    scrollable: list[ft.Control] = []
    if header is not None:
        scrollable.append(header)
    scrollable.extend(body)

    if footer is None:
        return theme.page_shell(*scrollable)

    return ft.Container(
        content=ft.Container(
            content=ft.Column(
                controls=[
                    ft.Container(
                        content=ft.Column(
                            controls=scrollable,
                            spacing=theme.Spacing.SM,
                            scroll=ft.ScrollMode.AUTO,
                            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                        ),
                        expand=True,
                    ),
                    footer,
                ],
                spacing=theme.Spacing.SM,
                expand=True,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            ),
            width=theme.MAX_CONTENT_WIDTH,
        ),
        alignment=ft.Alignment.TOP_CENTER,
        expand=True,
        padding=theme.page_padding(),
    )
