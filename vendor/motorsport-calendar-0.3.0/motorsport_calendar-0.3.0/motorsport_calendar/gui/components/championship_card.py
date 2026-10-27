"""ChampionshipCard — the one reusable race-card layout for the whole app.

Sprint 30: extracted out of ``gui/views/weekend.py`` so no view ever needs
to rebuild this layout again. Today it is used by Ce week-end; the same
card is meant for Favoris, Recherche, Tableau de bord, Calendrier,
Notifications and Historique whenever any of them need to show "a
championship's event" — same header, same session grid, same footer slot.

The component knows only ``ChampionshipCardData`` (this module's own model)
— never an ``Event``/``Session``/``Championship``/``Circuit`` domain object,
never a provider, never why/how the data was fetched. Callers (e.g.
``upcoming_weekend.py`` today; a future ``favorites.py``/``search.py``
controller tomorrow) are responsible for turning their own domain data into
this model. That is what keeps the component reusable: it never needs to
change when a *new* screen wants to show the same kind of card.

Sprint 32: ``circuit_name``/``country`` are optional. Deciding whether a
line is missing/redundant/"Unknown" is business logic (see
``gui/event_display.py``) that must never live here — this module only
renders whichever lines it is handed, skipping any that are ``None``.

Design: built entirely from existing ``theme.py`` primitives (``theme.card``,
``theme.Spacing``/``FontSize``/``Colors``) — no new colors, spacing values,
or tokens introduced.

Sprint 33: the championship name is preceded by its logo, resolved through
``championship_assets.get_championship_asset()`` — the component never
knows a file path or special-cases a championship id. When no logo is
available (unknown id, or a known id whose logo has not been delivered
yet) the title renders exactly as before, with no reserved empty space.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import flet as ft

from motorsport_calendar.gui import theme
from motorsport_calendar.gui.championship_assets import get_championship_asset


@dataclass(frozen=True)
class SessionRow:
    """One display-ready session line, e.g. "Essais Libres 1" / "Vendredi 10:30".

    Both fields are already-formatted strings (French label, local day+time)
    — the component does no formatting/translation of its own.
    """

    label: str
    day_time: str


@dataclass(frozen=True)
class ChampionshipCardData:
    """Everything one ChampionshipCard needs — pure presentation data.

    ``championship_id`` is not rendered; it is carried through so a future
    footer action (favori, notifications, export ICS, ...) knows which
    championship it applies to, without the component itself ever needing
    to look anything up.

    ``circuit_name``/``country`` are ``None`` when that line should not be
    shown at all (unknown, redundant with ``event_name``, or blank at the
    source) — deciding that is the caller's job (see
    ``gui/event_display.py``), never this module's.
    """

    championship_id: str
    championship_name: str
    event_name: str
    circuit_name: str | None
    country: str | None
    sessions: tuple[SessionRow, ...]


def _session_row(row: SessionRow) -> ft.Control:
    """One aligned "label ... time" line — label and time each anchored to
    their own end of the row, regardless of how long the label text is.
    """
    return ft.Row(
        [
            ft.Text(row.label, size=theme.FontSize.BODY, color=theme.Colors.TEXT_SECONDARY),
            ft.Text(row.day_time, size=theme.FontSize.BODY, weight=ft.FontWeight.W_500),
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
    )


def _header_title(data: ChampionshipCardData) -> ft.Control:
    """Championship name, preceded by its logo when the registry has one.

    No logo resolved (unknown id, or delivered-later id) -> the bare
    ``ft.Text`` exactly as before Sprint 33; no Row wrapper, no reserved
    space. This keeps every current card (no logo delivered yet) pixel
    identical to the pre-Sprint-33 layout.
    """
    title = ft.Text(data.championship_name, size=theme.FontSize.TITLE, weight=ft.FontWeight.BOLD)
    asset = get_championship_asset(data.championship_id)
    if asset.logo_src is None:
        return title

    logo = ft.Image(
        src=asset.logo_src,
        width=theme.IconSize.LG,
        height=theme.IconSize.LG,
        fit=ft.BoxFit.CONTAIN,
    )
    return ft.Row(
        [logo, title],
        spacing=theme.Spacing.XS,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )


def build_championship_card(
    data: ChampionshipCardData,
    *,
    footer: ft.Control | None = None,
    on_circuit_click: Callable[[], None] | None = None,
) -> ft.Control:
    """Return one ChampionshipCard as a themed, bordered card.

    Layout (fixed order, per the component spec):
      1. Header — championship name, event name, then circuit/country
         *if present* — a ``None`` value means that line is skipped
         entirely, never rendered blank or as "Unknown".
      2. Body — one aligned row per session (label, day + time).
      3. Footer — nothing by default.

    Args:
        data: the card's content — see ``ChampionshipCardData``.
        footer: optional extension point for future per-card actions
            (favori ⭐, notifications 🔔, export ICS, partage, résultats).
            When omitted (today, everywhere), no footer section is
            rendered at all — zero visual change until a caller opts in.
        on_circuit_click: optional extension point (Sprint 47) — when set
            *and* ``data.circuit_name is not None``, the circuit line
            becomes clickable (``theme.Colors.PRIMARY``, same semantic
            token as every other interactive element, no new color
            introduced) and calls this with no arguments on click. ``None``
            (default, every consumer but the "fiche événement" dialog)
            renders the exact same plain, non-interactive line as before
            this sprint — zero behavior change until a caller opts in,
            same contract as *footer*.
    """
    sections: list[ft.Control] = [
        _header_title(data),
        ft.Text(
            data.event_name,
            size=theme.FontSize.LABEL,
            weight=ft.FontWeight.W_500,
            color=theme.Colors.TEXT_SECONDARY,
        ),
    ]
    if data.circuit_name is not None:
        if on_circuit_click is None:
            sections.append(
                ft.Text(data.circuit_name, size=theme.FontSize.SMALL, color=theme.Colors.TEXT_MUTED)
            )
        else:
            sections.append(
                ft.Container(
                    content=ft.Text(
                        data.circuit_name,
                        size=theme.FontSize.SMALL,
                        weight=ft.FontWeight.W_500,
                        color=theme.Colors.PRIMARY,
                    ),
                    on_click=lambda e: on_circuit_click(),
                )
            )
    if data.country is not None:
        sections.append(
            ft.Text(data.country, size=theme.FontSize.SMALL, color=theme.Colors.TEXT_MUTED)
        )
    sections.append(ft.Divider(height=theme.Spacing.SM))
    sections.append(
        ft.Column(
            [_session_row(row) for row in data.sessions],
            spacing=theme.Spacing.XXS,
        )
    )

    if footer is not None:
        sections.append(ft.Divider(height=theme.Spacing.SM))
        sections.append(footer)

    return theme.card(ft.Column(sections, spacing=theme.Spacing.XXS))
