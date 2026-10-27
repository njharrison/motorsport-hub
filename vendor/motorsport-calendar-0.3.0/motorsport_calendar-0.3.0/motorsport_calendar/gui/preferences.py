"""Persistence of GUI user preferences between sessions.

Stored at: ``user_config_dir("motorsport-calendar")/gui_prefs.json`` —
``~/.config/motorsport-calendar/`` on Linux, ``%APPDATA%\\motorsport-calendar\\``
on Windows (Sprint 49, ``utils/paths.py``) — never inside the project/install
directory, which may be read-only once packaged.

Schema (all keys optional — missing keys fall back to _DEFAULTS):
  selected_championships: list[str]   IDs of checked championships
  last_output_dir:        str         Last directory used for saving the .ics
  favorite_championships: list[str]   IDs favorited (Sprint 44 — see
                                       gui/favorites_service.py::FavoritesService,
                                       the only code that should read/write
                                       this key)
  notifications_enabled:  bool        Notification engine on/off (Sprint 46 — see
                                       gui/notification_service.py::NotificationService,
                                       the only code that should read/write these
                                       3 keys)
  notifications_default_lead_time_minutes: int
                                       Default delay before a session, in minutes
  notifications_favorites_only: bool  Restrict notifications to favorited
                                       championships
  update_check_enabled:   bool        Update check on/off (Sprint 51 — see
                                       gui/update_service.py::UpdateService,
                                       gui/controller.py::check_for_update ;
                                       exposed on the Préférences page since
                                       Sprint 52, read/written directly —
                                       no dedicated service, a single flag
                                       needs none)
  default_year:            str        "current" (default) or a literal year
                                       string (Sprint 52 — see
                                       gui/models.py::resolve_default_year) ;
                                       seeds "Mon calendrier"'s initial year
                                       at launch, never goes stale like a
                                       baked-in year would
  ics_alarm_minutes:       int        VALARM reminder minutes before each
                                       session in exported .ics files
                                       (Sprint 52) — overrides
                                       ``config.ics.alarm_minutes`` for GUI
                                       exports only (``gui/controller.py::
                                       generate_calendar``) ; the CLI still
                                       reads only config.yaml, unaffected

The one centralized persistence file for all GUI state (Sprint 44,
ADR-035): every writer must read-modify-write (``load_preferences()``,
mutate only the key(s) it owns, ``save_preferences()`` the *whole* dict
back) rather than constructing a fresh literal — the latter silently wipes
whatever keys other writers already persisted.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from motorsport_calendar.utils.paths import user_config_dir

_PREFS_FILE: Path = user_config_dir("motorsport-calendar") / "gui_prefs.json"

_DEFAULTS: dict[str, Any] = {
    "selected_championships": ["formula1"],
    "last_output_dir": "",
    "favorite_championships": [],
    "notifications_enabled": False,
    "notifications_default_lead_time_minutes": 60,
    "notifications_favorites_only": False,
    "update_check_enabled": True,
    "default_year": "current",
    "ics_alarm_minutes": 30,
}


def load_preferences() -> dict[str, Any]:
    """Return saved preferences merged over defaults.

    On first run (no file) or corrupted JSON, returns a copy of _DEFAULTS.
    """
    try:
        data = json.loads(_PREFS_FILE.read_text(encoding="utf-8"))
        return {**_DEFAULTS, **data}
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return dict(_DEFAULTS)


def save_preferences(prefs: dict[str, Any]) -> None:
    """Persist preferences to disk. Silently swallows I/O errors."""
    try:
        _PREFS_FILE.parent.mkdir(parents=True, exist_ok=True)
        _PREFS_FILE.write_text(
            json.dumps(prefs, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except OSError:
        pass
