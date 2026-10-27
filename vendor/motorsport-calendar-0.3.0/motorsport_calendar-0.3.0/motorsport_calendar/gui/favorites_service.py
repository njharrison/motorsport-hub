"""FavoritesService — the single source of truth for favorite championships.

Sprint 44: favorites become a global application preference, automatically
used across the Dashboard, "Ce week-end", "Mon calendrier" and "Mes
favoris" — this service is the one place that owns reading/writing them,
so no other module ever touches the ``favorite_championships`` key of the
preferences file directly (see ``gui/preferences.py``'s own docstring).

Centralized persistence (per the sprint brief): backed by the exact same
preferences file as the rest of GUI state (``gui/preferences.py``), not a
second config file. Every mutation does a fresh read-modify-write —
``load_preferences()``, replace only ``favorite_championships``,
``save_preferences()`` the whole dict back — so a concurrent write of a
*different* key (e.g. "Mon calendrier" saving ``selected_championships``)
is never clobbered, and vice versa.

No Flet dependency — like ``ConfigService`` (``config/service.py``), this
is constructed fresh wherever it's needed (cheap local JSON read), never a
shared singleton passed around.
"""

from __future__ import annotations

from motorsport_calendar.gui.preferences import load_preferences, save_preferences


class FavoritesService:
    """Persisted, ordered set of favorite championship IDs.

    Order is insertion order (first favorited, first listed) — used as-is
    wherever favorites are displayed (e.g. "Mes favoris"); consumers that
    need a fast membership test should build a ``set``/``frozenset`` from
    ``list()`` themselves rather than calling ``is_favorite`` in a loop.
    """

    def __init__(self) -> None:
        self._favorites: list[str] = list(load_preferences().get("favorite_championships", []))

    def list(self) -> list[str]:
        """Favorite championship IDs, insertion order."""
        return list(self._favorites)

    def is_favorite(self, championship_id: str) -> bool:
        """True if *championship_id* is currently favorited."""
        return championship_id in self._favorites

    def add(self, championship_id: str) -> None:
        """Add *championship_id* to favorites. No-op if already favorited."""
        if championship_id not in self._favorites:
            self._favorites.append(championship_id)
            self._save()

    def remove(self, championship_id: str) -> None:
        """Remove *championship_id* from favorites. No-op if not favorited."""
        if championship_id in self._favorites:
            self._favorites.remove(championship_id)
            self._save()

    def toggle(self, championship_id: str) -> None:
        """Add *championship_id* if not favorited, remove it otherwise."""
        if self.is_favorite(championship_id):
            self.remove(championship_id)
        else:
            self.add(championship_id)

    def _save(self) -> None:
        prefs = load_preferences()
        prefs["favorite_championships"] = list(self._favorites)
        save_preferences(prefs)
