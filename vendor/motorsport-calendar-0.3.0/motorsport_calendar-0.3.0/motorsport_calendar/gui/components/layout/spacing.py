"""PageSpacing — a named, explicit one-off gap.

Prefer composing with ``Section``/``CardList``/``PageContainer`` first —
they already provide consistent spacing between the blocks they own. Reach
for this only for a genuine one-off visual break that isn't naturally
covered by one of those (e.g. before a wizard's action row). Keeps such
gaps self-documenting instead of a bare, unexplained
``ft.Container(height=...)`` scattered through a view.
"""

from __future__ import annotations

import flet as ft

from motorsport_calendar.gui import theme


def PageSpacing(size: int = theme.Spacing.MD) -> ft.Control:
    """Return a fixed-height spacer — defaults to the standard MD gap."""
    return ft.Container(height=size)
