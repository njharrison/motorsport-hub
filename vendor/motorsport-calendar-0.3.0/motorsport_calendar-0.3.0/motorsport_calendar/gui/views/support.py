"""🤝 Soutenir le projet — the contact point between Motorsport Calendar
and its community (Sprint 57, Préparation Beta).

Purely informative, per the brief: no local vote system, no local
donation system, no local suggestion form. Four sections:
  - "Soutenir Motorsport Calendar" — PayPal/GitHub Sponsors slots,
    prepared but not yet wired to a real URL (``ComingSoonRow``, the
    exact same "prepared, not yet real" shape ``views/preferences.py``'s
    Application section already uses — no new component).
  - "Voter pour les prochaines fonctionnalités" — a presentation only
    (``theme.chip`` per idea), never a local vote/counter.
  - "Suggestions" / "Signaler un problème" — one button each, opening
    GitHub Discussions/Issues via the shared ``gui/url_opener.py::
    make_url_opener`` (Sprint 57's own cleanup, also used by
    ``views/about.py``'s GitHub link).

No new service: this view (like ``views/about.py``) receives the raw
``url_launcher`` directly rather than a pre-wired callback from
main_view.py — an established exception to "views never build their own
handlers" for pages whose only interactivity is "open an external URL",
where main_view.py has no state/business logic to inject anyway.

All GitHub URLs are simple module-level constants — deliberately easy to
edit once real destinations exist (brief: "tous les liens doivent être
facilement configurables").
"""

from __future__ import annotations

import flet as ft

from motorsport_calendar.gui import theme
from motorsport_calendar.gui.components.layout import (
    ComingSoonRow,
    PageContainer,
    PageHeader,
    Section,
    SectionHeader,
)
from motorsport_calendar.gui.strings import STRINGS
from motorsport_calendar.gui.url_opener import make_url_opener

# Same repo as views/about.py's _GITHUB_URL — kept as its own constant
# here (not imported from about.py) so this page's links stay
# independently configurable, per the brief.
_GITHUB_REPO_URL = "https://github.com/naviss29/motorsport-calendar"
_GITHUB_DISCUSSIONS_URL = f"{_GITHUB_REPO_URL}/discussions"
_GITHUB_ISSUES_URL = f"{_GITHUB_REPO_URL}/issues"


def build_support_view(url_launcher: ft.UrlLauncher) -> ft.Control:
    """Return the "Soutenir le projet" page, through the Layout System.

    Args:
        url_launcher: Flet UrlLauncher service registered in page.services
            — same pattern as ``views/about.py``.
    """
    donate_rows = ft.Column(
        [
            ComingSoonRow(ft.Icons.PAYMENTS_OUTLINED, STRINGS.support_paypal_label),
            ComingSoonRow(ft.Icons.CARD_GIFTCARD_OUTLINED, STRINGS.support_github_sponsors_label),
        ],
        spacing=theme.Spacing.SM,
    )

    roadmap_chips = ft.Row(
        [theme.chip(idea) for idea in STRINGS.support_roadmap_ideas],
        spacing=theme.Spacing.XXS,
        wrap=True,
    )

    suggestions_button = ft.Button(
        content=STRINGS.support_suggestions_btn,
        icon=ft.Icons.FORUM_OUTLINED,
        on_click=make_url_opener(url_launcher, _GITHUB_DISCUSSIONS_URL),
    )

    report_button = ft.Button(
        content=STRINGS.support_report_btn,
        icon=ft.Icons.BUG_REPORT_OUTLINED,
        on_click=make_url_opener(url_launcher, _GITHUB_ISSUES_URL),
    )

    return PageContainer(
        header=PageHeader(STRINGS.nav_support, icon=ft.Icons.VOLUNTEER_ACTIVISM),
        body=[
            Section(
                ft.Text(
                    STRINGS.support_intro,
                    size=theme.FontSize.BODY,
                    color=theme.Colors.TEXT_SECONDARY,
                )
            ),
            Section(SectionHeader(STRINGS.support_section_donate), donate_rows),
            Section(
                SectionHeader(STRINGS.support_section_roadmap),
                ft.Text(
                    STRINGS.support_roadmap_intro,
                    size=theme.FontSize.SMALL,
                    color=theme.Colors.TEXT_MUTED,
                ),
                roadmap_chips,
            ),
            Section(
                SectionHeader(STRINGS.support_section_suggestions),
                ft.Text(
                    STRINGS.support_suggestions_text,
                    size=theme.FontSize.BODY,
                    color=theme.Colors.TEXT_SECONDARY,
                ),
                suggestions_button,
            ),
            Section(
                SectionHeader(STRINGS.support_section_report),
                ft.Text(
                    STRINGS.support_report_text,
                    size=theme.FontSize.BODY,
                    color=theme.Colors.TEXT_SECONDARY,
                ),
                report_button,
            ),
        ],
    )
