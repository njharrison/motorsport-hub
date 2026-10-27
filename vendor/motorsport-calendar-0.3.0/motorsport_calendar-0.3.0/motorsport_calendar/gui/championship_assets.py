"""Championship visual identity registry — Sprint 33.

Single entry point mapping a ``championship_id`` to its visual assets —
a logo today, possibly a color or an icon tomorrow. No view or component
is allowed to know a file path, or to special-case a specific
championship (``if championship_id == "formula1"``); they all call
``get_championship_asset()`` and render whatever comes back, including a
fully empty result.

Delivering an official logo later is a pure data change: drop the file at
``gui/assets/championships/<filename>`` (see the README in that folder)
— nothing in this module, in ``championship_card.py``, or in any view
needs to change.

No logo file exists in the repository yet (see
``gui/assets/championships/README.md``) — every championship therefore
resolves to ``logo_src=None`` today. Callers are required to handle
``None`` gracefully (no blank space, no broken-image placeholder); this
is the same contract already used for ``event_display.py``'s optional
metadata lines.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

_ASSETS_DIR = Path(__file__).parent / "assets" / "championships"

# Expected filename per championship_id. Purely descriptive — resolution
# below still checks the file actually exists before ever returning it.
_LOGO_FILENAMES: dict[str, str] = {
    "formula1": "formula1.png",
    "formula2": "formula2.png",
    "formula3": "formula3.png",
    "f1-academy": "f1-academy.png",
    "wec": "wec.png",
}


@dataclass(frozen=True)
class ChampionshipAsset:
    """Visual identity resolved for one ``championship_id``.

    ``logo_src`` is a Flet asset-relative path (e.g. ``"championships/
    formula1.png"``), ready to hand straight to ``ft.Image(src=...)``.
    It is ``None`` whenever there is nothing to show — unknown id, known
    id whose logo has not been delivered yet — callers never need to
    tell those two cases apart.
    """

    logo_src: str | None


def get_championship_asset(championship_id: str) -> ChampionshipAsset:
    """Resolve the visual identity for *championship_id*.

    Always returns a usable result, never raises: an unknown id and a
    known id without a delivered logo file both resolve to
    ``ChampionshipAsset(logo_src=None)``.
    """
    filename = _LOGO_FILENAMES.get(championship_id)
    if filename is None:
        return ChampionshipAsset(logo_src=None)

    if not (_ASSETS_DIR / filename).is_file():
        return ChampionshipAsset(logo_src=None)

    return ChampionshipAsset(logo_src=f"championships/{filename}")
