"""📅 Mon calendrier — calendar browser + ICS generation.

Sprint 26-42: a guided 4-step wizard (saison → championnats → destination →
créer). Sprint 43 replaced it entirely: the engine and every feature built
on top of it (filtering, the persistent selection summary, the season
explorer, the event details fiche) were already mature — the remaining
weak point was pure ergonomics, not capability. This sprint reorganizes the
same page around one flat layout instead of sequential steps:

  1. Championships are the entry point — displayed immediately under the
     title, grouped by category in single-level accordions
     (``ft.ExpansionTile``), each championship a selectable "button"
     (``theme.card(..., selected=...)``) rather than a checkbox in a long
     list.
  2. The season selector becomes a secondary, top-right control — the
     ``PageHeader``'s new ``trailing`` slot (Sprint 43), not the page's
     main element anymore.
  3. The selection summary (Sprint 40) is permanent — always rendered,
     never gated behind a step.
  4. The season explorer (Sprint 41) only appears once at least one
     championship is selected; otherwise an ``EmptyState``.
  5. "Créer mon calendrier" (plus the destination field it depends on)
     sits in a fixed footer (``PageContainer``'s new ``footer`` slot,
     Sprint 43) — always visible, never requiring a scroll of the whole
     page to reach.

None of the underlying logic changed: the selection summary numbers still
come from ``gui/calendar_selection.py``, the season explorer rows from
``gui/season_explorer.py``, the event details fiche from
``gui/event_details.py`` — this module still only arranges pre-computed
data/controls, exactly as before.

Sprint 44: the championship accordion itself (``ChampionshipButtonData``/
``ChampionshipCategoryData``/the accordion-of-buttons UI) moved to
``gui/components/championship_selector.py`` once "Mes favoris" needed the
exact same "pick some championships" UI — this module now only imports and
uses it, never redefines it.

Sprint 54 (Beta UX recette): the 3 tight value/label (or title/subtitle)
column spacings (``_summary_stat``, ``_selection_summary_block``'s period
column, ``_season_event_row``'s info column) now use
``theme.Spacing.XXS`` instead of a bare ``2`` — see ``views/
preferences.py``'s own Sprint 54 note for the same fix, same rationale.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import flet as ft

from motorsport_calendar.gui import theme
from motorsport_calendar.gui.components.championship_selector import (
    ChampionshipCategoryData,
    build_championship_selector,
)
from motorsport_calendar.gui.components.layout import (
    CardList,
    EmptyState,
    PageContainer,
    PageHeader,
    Section,
    SectionHeader,
)
from motorsport_calendar.gui.strings import STRINGS, plural

if TYPE_CHECKING:
    from motorsport_calendar.gui.calendar_selection import SelectionSummary
    from motorsport_calendar.gui.season_explorer import SeasonEventRow, SeasonMonthGroup


@dataclass
class CalendarViewControls:
    """Pre-built Flet controls + pure display data injected from
    main_view.py (which owns state + handlers).

    Separating layout (here) from state/handlers (main_view.py) keeps this
    module stateless and independently testable.
    """

    # Secondary, top-right controls (Sprint 43; refresh added MC-002 P0-7) —
    # no longer the page's main element.
    year_dropdown: ft.Dropdown
    refresh_btn: ft.IconButton

    # Fixed footer — destination + "Créer" action, always visible (Sprint 43).
    output_field: ft.TextField
    browse_btn: ft.IconButton
    generate_btn: ft.Button
    progress_ring: ft.ProgressRing
    error_text: ft.Text

    # Championships — the page's entry point (Sprint 43), grouped by
    # category in single-level accordions.
    category_groups: list[ChampionshipCategoryData] = field(default_factory=list)
    on_championship_click: Callable[[str], None] = field(default=lambda cid: None)
    on_category_toggle: Callable[[str, bool], None] = field(default=lambda cid, expanded: None)

    # Permanent selection summary (Sprint 40, always visible — Sprint 43).
    # ``None`` while controller.get_calendar_year_events for the current
    # year is still in flight (loading state), never while it is merely
    # empty (an empty selection or a selection with zero events is a
    # valid, non-loading SelectionSummary with event_count == 0).
    selection_summary: SelectionSummary | None = None
    # Always known instantly (len(selected_championships)) — shown even
    # while `selection_summary` above is still loading.
    selected_count: int = 0

    # Season explorer (Sprint 41) — visible only when >= 1 championship is
    # selected (Sprint 43), EmptyState otherwise. Same ``None`` = loading
    # convention as ``selection_summary`` above; an empty tuple means the
    # fetch resolved but nothing matches the current selection (including
    # "nothing selected").
    season_groups: tuple[SeasonMonthGroup, ...] | None = None
    # Fired with the clicked row (Sprint 42) — main_view.py looks the
    # underlying Event up via row.championship_id/row.event_uid and opens
    # the "fiche événement" dialog. No-op default.
    on_event_click: Callable[[SeasonEventRow], None] = field(default=lambda row: None)


def _summary_stat(value: str, label: str, *, expand: bool = False) -> ft.Control:
    return ft.Column(
        [
            ft.Text(
                value,
                size=theme.FontSize.HEADLINE,
                weight=ft.FontWeight.BOLD,
                color=theme.Colors.PRIMARY,
            ),
            ft.Text(label, size=theme.FontSize.CAPTION, color=theme.Colors.TEXT_MUTED),
        ],
        spacing=theme.Spacing.XXS,
        expand=expand,
    )


def _selection_summary_block(summary: SelectionSummary | None, selected_count: int) -> ft.Control:
    """Permanent "championships / events / sessions / period" summary
    (Sprint 40, always visible since Sprint 43 — no more per-step gating).

    Args:
        summary: ``None`` while ``controller.get_calendar_year_events`` for
            the current year is still in flight (loading state) — distinct
            from a resolved ``SelectionSummary`` with ``event_count == 0``
            (a genuinely empty selection, not a pending fetch).
        selected_count: ``len(state.selected_championships)`` — always
            known instantly, so it is shown in every state below, even
            while *summary* itself is still loading.
    """
    count_stat = _summary_stat(
        str(selected_count),
        STRINGS.calendar_summary_championships.format(s=plural(selected_count)),
    )

    if summary is None:
        return theme.card(
            ft.Row(
                [
                    count_stat,
                    ft.Row(
                        [
                            ft.ProgressRing(width=16, height=16),
                            ft.Text(
                                STRINGS.calendar_summary_loading,
                                size=theme.FontSize.BODY,
                                color=theme.Colors.TEXT_SECONDARY,
                            ),
                        ],
                        spacing=theme.Spacing.SM,
                    ),
                ],
                spacing=theme.Spacing.LG,
            )
        )

    if summary.event_count == 0:
        return theme.card(
            ft.Row(
                [
                    count_stat,
                    ft.Text(
                        STRINGS.calendar_summary_empty_selection,
                        size=theme.FontSize.BODY,
                        color=theme.Colors.TEXT_MUTED,
                    ),
                ],
                spacing=theme.Spacing.LG,
            )
        )

    if summary.period_start is not None and summary.period_end is not None:
        period_text = f"{summary.period_start:%d/%m/%Y} - {summary.period_end:%d/%m/%Y}"
    else:
        period_text = STRINGS.calendar_summary_period_empty

    return theme.card(
        ft.Row(
            [
                count_stat,
                _summary_stat(
                    str(summary.event_count),
                    STRINGS.calendar_summary_events.format(s=plural(summary.event_count)),
                ),
                _summary_stat(
                    str(summary.session_count),
                    STRINGS.calendar_summary_sessions.format(s=plural(summary.session_count)),
                ),
                ft.Column(
                    [
                        ft.Text(period_text, size=theme.FontSize.BODY, weight=ft.FontWeight.W_500),
                        ft.Text(
                            STRINGS.calendar_summary_period,
                            size=theme.FontSize.CAPTION,
                            color=theme.Colors.TEXT_MUTED,
                        ),
                    ],
                    spacing=theme.Spacing.XXS,
                    expand=True,
                ),
            ],
            spacing=theme.Spacing.LG,
        )
    )


def _season_event_row(
    row: SeasonEventRow, on_click: Callable[[SeasonEventRow], None]
) -> ft.Control:
    """One event as a compact, clickable row — separate lines per field
    (name, championship, circuit, country), never combined with a "·"
    separator (that combination was deliberately dropped from
    ChampionshipCard in Sprint 30 in favor of distinct lines — same rule
    applies here).

    Clicking opens the "fiche événement" (Sprint 42) — ``on_click`` is
    called with *row* itself; this function never resolves what happens
    next (that's main_view.py's job, via ``row.championship_id``/
    ``row.event_uid``)."""
    info_lines: list[ft.Control] = [
        ft.Text(row.event_name, size=theme.FontSize.LABEL, weight=ft.FontWeight.W_600),
        ft.Text(row.championship_name, size=theme.FontSize.SMALL, color=theme.Colors.TEXT_MUTED),
    ]
    if row.circuit_name:
        info_lines.append(
            ft.Text(row.circuit_name, size=theme.FontSize.SMALL, color=theme.Colors.TEXT_MUTED)
        )
    if row.country:
        info_lines.append(
            ft.Text(row.country, size=theme.FontSize.SMALL, color=theme.Colors.TEXT_MUTED)
        )

    card = theme.card(
        ft.Row(
            [
                ft.Column(info_lines, spacing=theme.Spacing.XXS, expand=True),
                ft.Text(
                    row.date_label, size=theme.FontSize.BODY, color=theme.Colors.TEXT_SECONDARY
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.START,
        )
    )
    card.on_click = lambda e: on_click(row)
    return card


def _season_explorer_block(
    groups: tuple[SeasonMonthGroup, ...] | None,
    on_event_click: Callable[[SeasonEventRow], None],
) -> ft.Control:
    """Season explorer — Sprint 41. Every event in the current selection,
    sorted chronologically and grouped by month. Sprint 43: visible only
    once at least one championship is selected — an empty *groups* (the
    same signal for "nothing selected" as "selection has zero events",
    both legitimately empty) renders an ``EmptyState`` either way.

    Args:
        groups: ``None`` while ``controller.get_calendar_year_events`` for
            the current year is still in flight (loading state) — distinct
            from a resolved empty tuple (fetch done, nothing matches the
            current selection, including "nothing selected").
        on_event_click: forwarded to every row (Sprint 42) — opens the
            "fiche événement" for the clicked event.
    """
    header = SectionHeader(STRINGS.calendar_season_explorer_title)

    if groups is None:
        return Section(
            header,
            theme.card(
                ft.Row(
                    [
                        ft.ProgressRing(width=16, height=16),
                        ft.Text(
                            STRINGS.calendar_season_explorer_loading,
                            size=theme.FontSize.BODY,
                            color=theme.Colors.TEXT_SECONDARY,
                        ),
                    ],
                    spacing=theme.Spacing.SM,
                )
            ),
        )

    if not groups:
        return Section(header, EmptyState(STRINGS.calendar_season_explorer_empty))

    month_blocks = [
        Section(
            SectionHeader(group.month_label),
            CardList([_season_event_row(row, on_event_click) for row in group.rows]),
        )
        for group in groups
    ]
    return Section(header, *month_blocks)


def _generate_footer(c: CalendarViewControls) -> ft.Control:
    """Destination + "Créer mon calendrier" — a fixed footer (Sprint 43),
    always visible without scrolling the whole page (``PageContainer``'s
    new ``footer`` slot). Previously the wizard's own step 3 (destination)
    and step 4 (create); merged here since there is no longer a notion of
    "step" to separate them into.
    """
    return ft.Column(
        [
            ft.Divider(height=theme.Spacing.SM),
            ft.Row(
                [c.output_field, c.browse_btn],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ft.Row(
                [c.generate_btn, c.progress_ring],
                alignment=ft.MainAxisAlignment.START,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=theme.Spacing.SM,
            ),
            c.error_text,
        ],
        spacing=theme.Spacing.SM,
    )


def build_calendar_view(c: CalendarViewControls) -> ft.Control:
    """Return the reorganized "Mon calendrier" page (Sprint 43).

    Layout, top to bottom: title + secondary year selector (top-right) →
    championships (entry point, accordions) → permanent selection summary
    → season explorer (or EmptyState) — all scrollable together — then a
    fixed footer (destination + "Créer") that never requires scrolling the
    rest of the page to reach.
    """
    return PageContainer(
        header=PageHeader(
            STRINGS.nav_my_calendar,
            icon=ft.Icons.CALENDAR_MONTH,
            trailing=ft.Row(
                [c.year_dropdown, c.refresh_btn],
                spacing=theme.Spacing.SM,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        ),
        body=[
            build_championship_selector(
                c.category_groups, c.on_championship_click, c.on_category_toggle
            ),
            _selection_summary_block(c.selection_summary, c.selected_count),
            _season_explorer_block(c.season_groups, c.on_event_click),
        ],
        footer=_generate_footer(c),
    )
