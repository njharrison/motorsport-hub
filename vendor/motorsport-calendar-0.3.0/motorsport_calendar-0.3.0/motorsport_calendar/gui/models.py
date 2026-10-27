"""GUI state and preference models — no business logic, no Flet dependency."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

# Sentinel value for the "default_year" preference (gui/preferences.py) —
# means "always today's year", never a year that goes stale as time passes.
# Any other stored value is a literal year string (e.g. "2027").
DEFAULT_YEAR_SENTINEL = "current"


def _current_year() -> int:
    return date.today().year


def resolve_default_year(value: str, *, current_year: int | None = None) -> int:
    """Decode the "default_year" preference into an actual year (Sprint 52).

    Args:
        value: the raw stored preference — ``DEFAULT_YEAR_SENTINEL`` or a
            literal year string (e.g. ``"2027"``).
        current_year: overrides ``date.today().year`` — for tests only.

    Returns:
        *current_year* (or today's year) for the sentinel or any value
        that isn't a valid integer (corrupted/hand-edited preferences
        file — never crash "Mon calendrier"'s startup over this); the
        parsed year otherwise.
    """
    resolved_current = current_year if current_year is not None else _current_year()
    if value == DEFAULT_YEAR_SENTINEL:
        return resolved_current
    try:
        return int(value)
    except ValueError:
        return resolved_current


@dataclass
class GenerateState:
    """Mutable state shared across the main view.

    Sprint 26-42: drove a 4-step wizard (``current_step``/``STEP_COUNT``/
    ``step_valid``/``can_advance``/``can_go_back``). Sprint 43 replaced the
    wizard with a single reorganized page (championships as the entry
    point, year as a secondary top-right control, a permanent selection
    summary, a conditional season explorer, and an always-visible "Créer"
    action) — there is no longer a notion of "step", so that machinery was
    removed. The remaining fields are exactly what the single page needs.
    """

    year: int = field(default_factory=_current_year)
    selected_championships: list[str] = field(default_factory=list)
    output_path: str = ""
    is_generating: bool = False

    def is_ready(self) -> bool:
        """True when all required fields are set and no generation is running."""
        return (
            bool(self.selected_championships) and bool(self.output_path) and not self.is_generating
        )


@dataclass(frozen=True)
class PreferencesModel:
    """Typed placeholder for the "Application" preferences (Sprint 52).

    Not yet persisted, not yet bound to ``gui/preferences.py`` — the
    Sprint 52 brief asks these to be *prepared* ("pensées pour évoluer"),
    not necessarily implemented: the Préférences page renders them as
    inert "coming soon" rows (see ``views/preferences.py::_PREF_ROWS``),
    but a typed model already exists so a future sprint that makes one of
    them real only has to wire persistence, not invent the shape.

    Sprint 26-51 history: this dataclass previously held
    ``language``/``timezone``/``first_day_of_week``/
    ``favorite_championships``/``preferred_calendar``/
    ``bapps_sync_enabled`` — all decorative, never bound to anything real
    (``favorite_championships`` in particular was fully superseded by
    ``FavoritesService`` at Sprint 44). Retired in favor of exactly the 3
    fields the Sprint 52 brief names for this "prepare only" bucket.

    Fields:
        theme:       UI theme slug (e.g. "dark", "light") — the app is
                     dark-only today (``page.theme_mode = ft.ThemeMode.DARK``
                     in ``main_view.py``), never read from here yet.
        language:    UI language code (e.g. "fr", "en") — ``strings.py``'s
                     ``Strings.from_dict`` already anticipates this, see
                     its own docstring; not wired to this field yet.
        time_format: "24h" or "12h" — no view formats a time string
                     conditionally on this yet.
    """

    theme: str = "dark"
    language: str = "fr"
    time_format: str = "24h"
