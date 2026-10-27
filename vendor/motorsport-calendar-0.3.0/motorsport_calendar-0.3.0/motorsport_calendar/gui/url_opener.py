"""url_opener — the one "open this URL in the system browser" helper
(Sprint 57 — Préparation Beta, nettoyage).

Before this sprint, the exact same try/``url_launcher.launch_url``/except/
``subprocess.Popen`` Windows fallback existed independently in 2 places
(``views/about.py``'s GitHub link, Sprint 26; ``main_view.py::
_make_release_opener``, Sprint 51/53) and was about to become a 3rd copy
for "Soutenir le projet"'s GitHub Discussions/Issues buttons. Promoted here
once a 3rd real call site made the duplication concrete rather than
theoretical — same "mutualize on the second/third real use" principle
already applied throughout this project (providers, ChampionshipCard,
championship_selector, ``_open_event_details``/``_open_circuit_details``).

No Flet control is built here — this only returns the ``on_click``
callable a caller wires onto whichever button/link it owns.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
import subprocess
import sys

import flet as ft


def make_url_opener(
    url_launcher: ft.UrlLauncher, url: str
) -> Callable[[ft.ControlEvent], Awaitable[None]]:
    """Return an ``on_click`` handler that opens *url* in the system browser.

    Tries ``url_launcher.launch_url`` (the normal path on every platform);
    falls back to ``subprocess.Popen("start ...")`` on Windows if it fails
    (some Windows/Flet combinations have been observed not to register the
    URL protocol handler). Never raises on either path — a broken browser
    launch must never crash the app, only silently do nothing.
    """

    async def opener(e: ft.ControlEvent) -> None:
        try:
            await url_launcher.launch_url(url)
        except Exception:
            if sys.platform == "win32":
                subprocess.Popen(f"start {url}", shell=True)

    return opener
