"""Championship ID → user-readable display names.

Intentionally lives in the GUI layer only.
Never imports from providers — the mapping is presentation-only.
"""

from __future__ import annotations

_DISPLAY_NAMES: dict[str, str] = {
    "formula1": "Formula 1",
    "formula2": "Formula 2",
    "formula3": "Formula 3",
    "f1-academy": "F1 Academy",
    "formula-e": "Formula E",
    "wec": "FIA WEC",
    "porsche-supercup": "Porsche Supercup",
    "elms": "European Le Mans Series",
    "mlmc": "Michelin Le Mans Cup",
    "imsa": "IMSA WeatherTech SportsCar Championship",
    "gtwc-europe": "GT World Challenge Europe",
    "gtwc-america": "GT World Challenge America",
    "gtwc-asia": "GT World Challenge Asia",
    "igtc": "Intercontinental GT Challenge",
    "motogp": "MotoGP",
    "moto2": "Moto2",
    "moto3": "Moto3",
    "worldsbk": "WorldSBK",
}

# Championships pre-selected at first launch (no saved preferences found)
DEFAULT_SELECTED: list[str] = ["formula1"]


def get_display_name(championship_id: str) -> str:
    """Return the user-facing name for a championship ID.

    Falls back to title-casing the ID when no explicit mapping exists.
    """
    return _DISPLAY_NAMES.get(
        championship_id,
        championship_id.replace("-", " ").title(),
    )
