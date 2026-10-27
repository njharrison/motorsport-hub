"""🔍 Recherche — global, instant, offline search (Sprint 45).

Anticipated since Sprint 31 (see ``gui/components/layout/section.py``'s/
``card_list.py``'s/``empty_state.py``'s own docstrings, and
``test_gui_components_layout.py``'s "Recherche" example composition) —
this is the first real consumer of that anticipated page shape:
``PageHeader(title, icon=ft.Icons.SEARCH, subtitle="N résultats")`` +
``Section``/``SectionHeader``/``CardList`` per result group +
``EmptyState`` when nothing matches. No new component.

Pure layout only: the search field is a pre-built control injected from
main_view.py (same pattern as ``year_dropdown``/``output_field`` on "Mon
calendrier"), and ``SearchResults`` is already grouped/sorted by
``gui/search_service.py`` — this module never searches, sorts, or decides
what "matches", it only renders what it's given.

Sprint 54 (Beta UX recette): ``_result_row``'s title/subtitle spacing now
uses ``theme.Spacing.XXS`` instead of a bare ``2`` — see ``views/
preferences.py``'s own Sprint 54 note for the same fix, same rationale.

Sprint 55 (Recherche interactive): result cards become clickable —
``on_championship_click``/``on_event_click``/``on_circuit_click`` are
each called with the clicked ``SearchResultItem`` itself (never a
resolved domain object; same "identity carried through, view never
resolves it" convention as ``views/calendar.py``'s
``on_event_click(row: SeasonEventRow)``). This module still decides
nothing about *what* clicking means — it only wires the right callback
to the right section, main_view.py owns every actual resolution
(``EventDetails``/``CircuitService``/navigation).
"""

from __future__ import annotations

from collections.abc import Callable

import flet as ft

from motorsport_calendar.gui import theme
from motorsport_calendar.gui.components.layout import (
    CardList,
    EmptyState,
    PageContainer,
    PageHeader,
    Section,
    SectionHeader,
)
from motorsport_calendar.gui.search_service import SearchResultItem, SearchResults
from motorsport_calendar.gui.strings import STRINGS, plural

_ResultClickHandler = Callable[[SearchResultItem], None]


def _result_row(item: SearchResultItem, on_click: _ResultClickHandler | None) -> ft.Control:
    lines: list[ft.Control] = [
        ft.Text(item.title, size=theme.FontSize.BODY, weight=ft.FontWeight.W_600)
    ]
    if item.subtitle:
        lines.append(
            ft.Text(item.subtitle, size=theme.FontSize.SMALL, color=theme.Colors.TEXT_MUTED)
        )
    card = theme.card(ft.Column(lines, spacing=theme.Spacing.XXS))
    if on_click is not None:
        card.on_click = lambda e: on_click(item)
    return card


def _result_section(
    label: str, items: tuple[SearchResultItem, ...], on_click: _ResultClickHandler | None
) -> ft.Control | None:
    if not items:
        return None
    return Section(SectionHeader(label), CardList([_result_row(item, on_click) for item in items]))


def build_search_view(
    search_field: ft.TextField,
    results: SearchResults,
    has_query: bool,
    *,
    on_championship_click: _ResultClickHandler | None = None,
    on_event_click: _ResultClickHandler | None = None,
    on_circuit_click: _ResultClickHandler | None = None,
) -> ft.Control:
    """Return the "Recherche" page, through the Layout System.

    Args:
        search_field: pre-built ``ft.TextField`` (main_view.py owns its
            ``on_change`` handler — instant search while typing).
        results: already searched, grouped, and sorted by
            ``gui/search_service.py::SearchService`` — this function only
            arranges it.
        has_query: distinguishes "nothing typed yet" from "searched but
            found nothing" — both render an ``EmptyState``, with a
            different message (Sprint 45's own "recherche vide" vs
            "aucun résultat" validation scenarios).
        on_championship_click: called with the clicked
            ``SearchResultItem`` (``championship_id`` set) — main_view.py
            decides what "open this championship" means (Sprint 55:
            navigates to "Mon calendrier", the closest existing
            destination — there is no dedicated per-championship page).
        on_event_click: called with the clicked ``SearchResultItem``
            (``championship_id``/``event_uid`` set) — main_view.py
            resolves the underlying ``Event`` and opens the existing
            "fiche événement" (Sprint 42), same resolution
            ``views/calendar.py``'s season explorer already uses.
        on_circuit_click: called with the clicked ``SearchResultItem``
            (``circuit_key`` set) — main_view.py opens the existing
            "fiche Circuit" (Sprint 47).
        Each callback is ``None`` (default) only in tests/loading states
        that never wire interaction — every real call site in
        main_view.py passes all three.
    """
    subtitle = None
    if has_query and not results.is_empty:
        subtitle = STRINGS.search_results_count.format(
            n=results.total_count, s=plural(results.total_count)
        )

    body: list[ft.Control] = [search_field]

    sections = [
        section
        for section in (
            _result_section(
                STRINGS.search_section_championships, results.championships, on_championship_click
            ),
            _result_section(STRINGS.search_section_events, results.events, on_event_click),
            _result_section(STRINGS.search_section_circuits, results.circuits, on_circuit_click),
        )
        if section is not None
    ]

    if sections:
        body.extend(sections)
    elif has_query:
        body.append(EmptyState(STRINGS.search_no_results))
    else:
        body.append(EmptyState(STRINGS.search_empty_query))

    return PageContainer(
        header=PageHeader(STRINGS.nav_search, icon=ft.Icons.SEARCH, subtitle=subtitle),
        body=body,
    )
