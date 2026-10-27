"""Flet desktop application entry point.

Usage:
    motocal-gui
    python -m motorsport_calendar.gui

Assets (Sprint 49 — Brand Set v1.0, see gui/assets/logo/README.md): served
from ``gui/assets/`` — icon.png/icon_windows.ico (window/taskbar icon,
``page.window.icon`` set in ``main_view.py``), favicon-16/32.png, and
``logo/`` (mc-icon.svg/logo-horizontal.svg/logo-vertical.svg, not yet
consumed by any view — see that README for the anticipated call sites,
unchanged this sprint: no Design System evolution).
"""

from __future__ import annotations

from pathlib import Path

# Flet's own ``assets_dir`` resolves relative strings against the current
# working directory at launch time, not against this file's location
# (confirmed: ``flet/app.py``'s ``__get_assets_dir_path(..., relative_to_cwd=True)``)
# — a packaged/installed ``motocal-gui`` can be launched from anywhere, so a
# CWD-relative string would silently fail to find the assets outside this
# project's own directory. Resolved from ``__file__`` instead: portable
# across machines/install locations, never a literal hardcoded path.
_ASSETS_DIR = str(Path(__file__).parent / "assets")


def main() -> None:
    """Launch the Motorsport Calendar desktop GUI."""
    try:
        import flet as ft
    except ImportError:
        import sys

        sys.exit(
            "Flet is required for the GUI.\nInstall it with:  pip install motorsport-calendar[gui]"
        )

    from motorsport_calendar.gui.main_view import build_main_view

    ft.run(
        main=build_main_view,
        view=ft.AppView.FLET_APP,
        assets_dir=_ASSETS_DIR,
    )


if __name__ == "__main__":
    main()
