"""Cross-platform user directories — cache and config/preferences (Sprint 49).

A packaged, distributed app must never write inside its own install
directory (often read-only, e.g. ``Program Files`` on Windows or a
read-only mount elsewhere) and must never depend on the project's Git
repository being present — every persisted file (GUI preferences, HTTP
cache, ``config.yaml`` lookup) needs an OS-appropriate user directory
instead. Mirrors the ``sys.platform`` convention already established in
``gui/main_view.py::_open_folder``/``gui/views/about.py`` — no new
dependency for something this small.

Windows: ``%APPDATA%`` (roaming — settings, safe to sync/backup) vs
``%LOCALAPPDATA%`` (local-only — cache, safe to clear without data loss).
Linux (XDG Base Directory spec): ``$XDG_CONFIG_HOME`` (default
``~/.config``) vs ``$XDG_CACHE_HOME`` (default ``~/.cache``) — same
distinction. macOS is not a packaging target for this project (Sprint 49
scope: Linux + Windows only) but falls back to the same XDG-style
convention rather than raising.
"""

from __future__ import annotations

import os
from pathlib import Path
import sys


def user_config_dir(app_name: str) -> Path:
    """Directory for persisted user settings (GUI preferences, config.yaml).

    Windows: ``%APPDATA%\\{app_name}``. Linux/other: ``$XDG_CONFIG_HOME/
    {app_name}`` (default ``~/.config/{app_name}``).
    """
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        base = Path(appdata) if appdata else Path.home() / "AppData" / "Roaming"
    else:
        xdg = os.environ.get("XDG_CONFIG_HOME")
        base = Path(xdg) if xdg else Path.home() / ".config"
    return base / app_name


def user_cache_dir(app_name: str) -> Path:
    """Directory for disposable cached data (HTTP cache) — safe to clear.

    Windows: ``%LOCALAPPDATA%\\{app_name}``. Linux/other:
    ``$XDG_CACHE_HOME/{app_name}`` (default ``~/.cache/{app_name}``).
    """
    if sys.platform == "win32":
        localappdata = os.environ.get("LOCALAPPDATA")
        base = Path(localappdata) if localappdata else Path.home() / "AppData" / "Local"
    else:
        xdg = os.environ.get("XDG_CACHE_HOME")
        base = Path(xdg) if xdg else Path.home() / ".cache"
    return base / app_name
