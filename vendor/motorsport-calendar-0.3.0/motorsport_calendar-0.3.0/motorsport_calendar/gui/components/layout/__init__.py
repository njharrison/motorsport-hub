"""Layout System — the structural components every view is built from.

Sprint 31. Before this package existed, every view in ``gui/views/*.py``
built its own page container (width/padding/alignment), its own header
(icon + title + divider), and its own card wrapping for empty states — five
near-identical, slowly-diverging implementations of the same ideas.

This package is the fix: a small set of single-responsibility components
that any current or future view composes instead of rebuilding:

    return PageContainer(
        header=PageHeader("Ce week-end", icon=ft.Icons.SPORTS_MOTORSPORTS),
        body=[Section(CardList(cards))],
    )

- ``PageContainer`` — max width, padding, alignment. Nothing else.
- ``PageHeader``    — icon, title, optional subtitle, trailing separator.
- ``Section``       — the standard gap between related blocks.
- ``SectionHeader`` — a smaller heading *inside* a Section (not the page's
  own title — that's PageHeader's job).
- ``CardList``      — a uniform vertical list of cards.
- ``EmptyState``    — the one "nothing here yet" card, shared by every
  empty page today and tomorrow.
- ``PageSpacing``   — a named, explicit one-off gap, for the rare case
  none of the above already covers it.
- ``ComingSoonRow`` — icon + label + a muted "Disponible prochainement"
  chip, for any setting/link that is prepared but not yet wired to
  something real (Sprint 57 — promoted from ``views/preferences.py``'s
  own ``_pref_row`` once "Soutenir le projet" needed the identical shape
  for its PayPal/GitHub Sponsors slots).

Every component here is built exclusively from ``gui/theme.py``'s existing
tokens and primitives — no new colors, spacing values, or design tokens are
introduced by this package.
"""

from .card_list import CardList
from .coming_soon_row import ComingSoonRow
from .empty_state import EmptyState
from .page_container import PageContainer
from .page_header import PageHeader
from .section import Section, SectionHeader
from .spacing import PageSpacing

__all__ = [
    "CardList",
    "ComingSoonRow",
    "EmptyState",
    "PageContainer",
    "PageHeader",
    "PageSpacing",
    "Section",
    "SectionHeader",
]
