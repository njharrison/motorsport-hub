"""Motorsport Calendar Design System — Release Alpha Phase 2.

Single source of truth for every visual token used by `gui/views/*` and
`gui/main_view.py`: colors, spacing, radii, icon sizes, typography sizes,
and shared component builders (buttons, cards, chips, section titles).

No view should hardcode a `ft.Colors.*`, a raw padding int, or a border
radius — it should import the matching token from this module instead.
That way a single edit here changes the whole app consistently.

Color sources (brand set validated by BApps-Studio, see docs/JOURNAL.md
Sprint 26 for the audit trail):
  - BAppsColors     -> BApps-Studio/02-Brand/BrandGuide.md   (ecosystem-wide)
  - MotorsportColors -> BApps-Studio/03-Products/Motorsport-Calendar/
                         Branding/Branding.md                 (product-specific)

The final logo/icon SVGs from the validated Brand Set are not wired in yet
(see gui/assets/logo/README.md) — `logo_placeholder()` stands in for them
so the design system does not block on asset delivery.
"""

from __future__ import annotations

import flet as ft

# ============================================================================
# COLORS
# ============================================================================


class BAppsColors:
    """Ecosystem-wide BApps brand colors (shared by every BApps product)."""

    BLUE = "#0A84FF"
    CYAN = "#39D0FF"
    BG_DARK = "#111827"
    BG_LIGHT = "#F8FAFC"
    TEXT_PRIMARY = "#FFFFFF"
    TEXT_SECONDARY = "#94A3B8"


class MotorsportColors:
    """Motorsport Calendar product palette (Brand Set v1.0)."""

    BLUE = "#007AFF"
    CYAN = "#00E5FF"
    BLUE_DARK = "#0052CC"
    MIDNIGHT = "#0B1220"
    SURFACE_DARK = "#1A2433"
    SURFACE_LIGHT = "#E5E7EB"
    WHITE = "#FFFFFF"


class Colors:
    """Semantic color roles — the only palette views should consume directly.

    Maps abstract roles (primary, surface, border...) onto the brand
    palettes above, so a future brand tweak never requires touching a view.
    """

    PRIMARY = MotorsportColors.BLUE
    ACCENT = MotorsportColors.CYAN
    CTA = ft.Colors.GREEN_700  # "Créer mon calendrier" — positive action
    CTA_HOVER = ft.Colors.GREEN_600
    SUCCESS = ft.Colors.GREEN_400
    ERROR = ft.Colors.RED_400
    WARNING = ft.Colors.AMBER_400

    BACKGROUND = MotorsportColors.MIDNIGHT
    SURFACE = MotorsportColors.SURFACE_DARK
    BORDER = ft.Colors.WHITE_12
    BORDER_ACTIVE = MotorsportColors.BLUE

    TEXT_PRIMARY = ft.Colors.WHITE
    TEXT_SECONDARY = ft.Colors.WHITE_70
    TEXT_MUTED = ft.Colors.WHITE_54
    TEXT_DISABLED = ft.Colors.WHITE_38
    TEXT_GHOST = ft.Colors.WHITE_30


# ============================================================================
# SPACING — 4px base scale
# ============================================================================


class Spacing:
    """4px-base spacing scale — the only source of padding/gap values."""

    XXS = 4
    XS = 8
    SM = 12
    MD = 16
    LG = 24
    XL = 32
    XXL = 48


# ============================================================================
# RADIUS
# ============================================================================


class Radius:
    """Border-radius scale — the only source of corner-rounding values."""

    SM = 6
    MD = 8
    LG = 12
    PILL = 999


# ============================================================================
# ICON SIZES
# ============================================================================


class IconSize:
    """Icon-size scale — the only source of icon pixel sizes."""

    SM = 16
    MD = 20
    LG = 24
    XL = 48


# ============================================================================
# TYPOGRAPHY
# ============================================================================


class FontSize:
    """Typography scale — the only source of font-size values."""

    CAPTION = 11
    SMALL = 12
    BODY = 13
    LABEL = 14
    SUBTITLE = 15
    TITLE = 18
    HEADLINE = 20
    DISPLAY = 24


# ============================================================================
# PAGE LAYOUT
# ============================================================================

# Sprint 27 — single shared grid for every top-level view. The content
# column never grows wider than this, so it stays readable and consistent
# regardless of window size; on narrow windows it simply shrinks to fit.
MAX_CONTENT_WIDTH = 1000


def page_padding() -> ft.Padding:
    """Standard outer padding shared by every top-level view container."""
    return ft.Padding.symmetric(vertical=Spacing.LG, horizontal=Spacing.XL)


def page_shell(*sections: ft.Control) -> ft.Control:
    """The one page grid every view (Ce week-end, Mon calendrier, Mes favoris,
    Préférences, À propos) renders through — Sprint 27.

    Centers a single max-width column horizontally in the window; the
    centering stops there — everything inside is stacked and left-aligned,
    never centered mid-screen. This is the only place window-width handling
    lives, so every page shares identical margins, section spacing and
    max width by construction instead of by convention.
    """
    return ft.Container(
        content=ft.Container(
            content=ft.Column(
                controls=list(sections),
                spacing=Spacing.SM,
                scroll=ft.ScrollMode.AUTO,
                expand=True,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            ),
            width=MAX_CONTENT_WIDTH,
        ),
        alignment=ft.Alignment.TOP_CENTER,
        expand=True,
        padding=page_padding(),
    )


def section_title(text: str, *, icon: ft.IconData | None = None) -> ft.Control:
    """Page header: optional icon + bold title, used at the top of every view."""
    controls: list[ft.Control] = []
    if icon is not None:
        controls.append(ft.Icon(icon, size=IconSize.LG, color=Colors.PRIMARY))
    controls.append(ft.Text(text, size=FontSize.TITLE, weight=ft.FontWeight.BOLD))
    return ft.Row(controls, spacing=Spacing.XS, vertical_alignment=ft.CrossAxisAlignment.CENTER)


# ============================================================================
# COMPONENT BUILDERS
# ============================================================================


def button_style(variant: str = "primary") -> ft.ButtonStyle:
    """Shared button styles. Variants: "primary" (brand blue), "cta" (create
    action, green), "ghost" (transparent, low-emphasis).
    """
    variants = {
        "primary": ft.ButtonStyle(bgcolor=Colors.PRIMARY, color=Colors.TEXT_PRIMARY),
        "cta": ft.ButtonStyle(bgcolor=Colors.CTA, color=Colors.TEXT_PRIMARY),
        "ghost": ft.ButtonStyle(bgcolor=ft.Colors.TRANSPARENT, color=Colors.TEXT_SECONDARY),
    }
    return variants[variant]


def card(
    content: ft.Control,
    *,
    width: int | None = None,
    padding: int = Spacing.MD,
    selected: bool = False,
) -> ft.Container:
    """Standard bordered card used for placeholder blocks, rows and summaries.

    `selected=True` highlights the card with the brand border + tinted surface
    (used for step indicators and chosen options in the calendar wizard).
    """
    return ft.Container(
        content=content,
        padding=ft.Padding.all(padding),
        border_radius=Radius.MD,
        border=ft.Border.all(1, Colors.BORDER_ACTIVE if selected else Colors.BORDER),
        bgcolor=Colors.SURFACE if selected else None,
        width=width,
    )


def chip(text: str) -> ft.Control:
    """Small rounded label — e.g. "Disponible prochainement"."""
    return ft.Container(
        content=ft.Text(text, size=FontSize.CAPTION, color=Colors.TEXT_DISABLED),
        padding=ft.Padding.symmetric(horizontal=Spacing.XS, vertical=3),
        border_radius=Radius.PILL,
        border=ft.Border.all(1, Colors.BORDER),
    )


def logo_placeholder(kind: str = "icon", *, size: int = IconSize.XL) -> ft.Control:
    """Temporary stand-in for the validated Brand Set logo assets.

    The final SVGs (`logo-horizontal.svg`, `mc-icon.svg`) are not wired into
    the app yet — see `gui/assets/logo/README.md`. This placeholder keeps the
    exact spot each asset will occupy so swapping them in later is a one-line
    change in each view, not a layout rework.

    Args:
        kind: "icon" — square MC monogram badge (nav rail, About, headers).
              "horizontal" — wide placeholder bar (future horizontal wordmark).
    """
    if kind == "horizontal":
        return ft.Container(
            content=ft.Row(
                [
                    logo_placeholder("icon", size=Spacing.XL),
                    ft.Text(
                        "Motorsport Calendar",
                        size=FontSize.LABEL,
                        weight=ft.FontWeight.W_600,
                        color=Colors.TEXT_PRIMARY,
                    ),
                ],
                spacing=Spacing.XS,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.Padding.symmetric(horizontal=Spacing.SM, vertical=Spacing.XXS),
        )

    return ft.Container(
        content=ft.Text(
            "MC",
            size=size * 0.42,
            weight=ft.FontWeight.BOLD,
            color=Colors.TEXT_PRIMARY,
        ),
        width=size,
        height=size,
        border_radius=Radius.MD,
        gradient=ft.LinearGradient(
            begin=ft.Alignment.TOP_LEFT,
            end=ft.Alignment.BOTTOM_RIGHT,
            colors=[MotorsportColors.BLUE, MotorsportColors.CYAN],
        ),
        alignment=ft.Alignment.CENTER,
        tooltip="Placeholder — futur logo Motorsport Calendar",
    )
