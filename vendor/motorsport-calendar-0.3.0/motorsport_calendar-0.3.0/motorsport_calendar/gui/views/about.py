"""À propos — about screen view.

Extracted from main_view.py so each view stays in its own module.
Requires url_launcher to open the GitHub link.

Sprint 28: compacted — the app name + version serve as the page's own
heading (no separate generic "À propos" label above them). Sprint 31: now
composed via the Layout System's ``PageContainer`` (no ``header=`` — this
page deliberately keeps its compact branding block as content rather than
the standard ``PageHeader``, unchanged from Sprint 28) + ``Section`` for
its content, instead of building its own container/spacing directly.

Sprint 54 (Beta UX recette): the version line now carries the actual
``motorsport_calendar.__version__`` (e.g. "Version 0.2.0 — Alpha") instead
of a bare "Version Alpha" with no number — the Dashboard's "État" section
(Sprint 53) already shows this exact same value; À propos was the one
place in the app that talked about "the version" without ever saying
which one. ``version`` defaults to the real ``__version__`` so every
existing caller is unaffected.

Sprint 57 (Préparation Beta — positionnement): À propos becomes a real
presentation of the project — objectifs, philosophie Open Source,
technologies utilisées — added as ``Section``s below the unchanged
branding/description/GitHub/license block, through the same Layout
System primitives every other multi-section page already uses
(``Section``/``SectionHeader``/``theme.card``/``theme.chip``). The
GitHub link's ``on_click`` now comes from ``gui/url_opener.py::
make_url_opener`` instead of its own inline closure — that fallback
logic used to exist independently here and in ``main_view.py::
_make_release_opener``; a 3rd real call site (this sprint's "Soutenir le
projet" page) made the duplication concrete enough to mutualize.
"""

from __future__ import annotations

import flet as ft

from motorsport_calendar.gui import theme
from motorsport_calendar.gui.components.layout import PageContainer, Section, SectionHeader
from motorsport_calendar.gui.strings import STRINGS
from motorsport_calendar.gui.url_opener import make_url_opener

_GITHUB_URL = "https://github.com/naviss29/motorsport-calendar"


def build_about_view(url_launcher: ft.UrlLauncher, *, version: str | None = None) -> ft.Control:
    """Return the À propos view, through the Layout System.

    Args:
        url_launcher: Flet UrlLauncher service registered in page.services.
        version: defaults to ``motorsport_calendar.__version__`` — override
            only used by tests that want a deterministic value.
    """
    if version is None:
        from motorsport_calendar import __version__ as version

    on_github_click = make_url_opener(url_launcher, _GITHUB_URL)

    branding_row = ft.Row(
        [
            theme.logo_placeholder("icon", size=theme.IconSize.XL),
            ft.Column(
                [
                    ft.Text(
                        STRINGS.app_title,
                        size=theme.FontSize.TITLE,
                        weight=ft.FontWeight.BOLD,
                    ),
                    ft.Text(
                        STRINGS.about_version.format(version=version),
                        size=theme.FontSize.SMALL,
                        color=theme.Colors.TEXT_MUTED,
                    ),
                ],
                spacing=theme.Spacing.XXS,
            ),
        ],
        spacing=theme.Spacing.SM,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    description = ft.Text(
        STRINGS.about_description,
        size=theme.FontSize.BODY,
        color=theme.Colors.TEXT_SECONDARY,
    )

    developer = ft.Text(
        STRINGS.about_developer,
        size=theme.FontSize.LABEL,
        weight=ft.FontWeight.W_500,
    )

    github_row = ft.Row(
        [
            ft.TextButton(
                content=ft.Row(
                    [
                        ft.Icon(ft.Icons.OPEN_IN_NEW, size=theme.IconSize.SM),
                        ft.Text(STRINGS.about_github_label, size=theme.FontSize.BODY),
                    ],
                    spacing=theme.Spacing.XXS,
                    tight=True,
                ),
                on_click=on_github_click,
            )
        ],
        alignment=ft.MainAxisAlignment.START,
    )

    license_text = ft.Text(
        STRINGS.about_license,
        size=theme.FontSize.SMALL,
        color=theme.Colors.TEXT_GHOST,
    )

    objectives_card = theme.card(
        ft.Column(
            [
                ft.Text(f"• {line}", size=theme.FontSize.BODY, color=theme.Colors.TEXT_SECONDARY)
                for line in STRINGS.about_objectives
            ],
            spacing=theme.Spacing.XS,
        )
    )

    open_source_card = theme.card(
        ft.Text(
            STRINGS.about_open_source_text,
            size=theme.FontSize.BODY,
            color=theme.Colors.TEXT_SECONDARY,
        )
    )

    tech_chips = ft.Row(
        [theme.chip(name) for name in STRINGS.about_tech_stack],
        spacing=theme.Spacing.XXS,
        wrap=True,
    )

    return PageContainer(
        body=[
            Section(branding_row, description, developer, github_row, license_text),
            Section(SectionHeader(STRINGS.about_section_objectives), objectives_card),
            Section(SectionHeader(STRINGS.about_section_open_source), open_source_card),
            Section(SectionHeader(STRINGS.about_section_tech), tech_chips),
        ],
    )
