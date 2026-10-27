"""System notifications — the one OS-dependent layer for real notification
delivery (Sprint 56).

``gui/notification_service.py`` (Sprint 46) already computes *what*/*when*
to notify — a platform-agnostic ``Notification`` — and stays that way: it
must never import this module, never know "Windows"/"Linux"/"macOS". This
module is the only place in the whole app allowed to know that a platform
exists at all, and it decides exactly one thing: *how* (or whether) a
computed ``Notification`` becomes a real, visible OS notification.

Verified fact, not a hypothesis (checked against the installed
``flet==0.85.3`` package before writing a line of this module): Flet ships
no system/OS notification service on any platform. Its full service-control
roster (``flet.controls.services.*``) is accelerometer, barometer, battery,
browser_context_menu, clipboard, connectivity, file_picker, gyroscope,
haptic_feedback, magnetometer, screen_brightness, semantics_service,
shake_detector, shared_preferences, share, storage_paths, url_launcher,
user_accelerometer, wakelock — 20 services, none of them "notification" or
"toast" or "tray". ``ft.Window`` has no tray-icon/balloon-notification API
either (its full method surface is ``wait_until_ready_to_show``/
``destroy``/``center``/``close``/``to_front``/``start_dragging``/
``start_resizing`` — nothing notification-shaped). Flet's own Dart-side
changelog (``CHANGELOG.md`` bundled with the pub.dev package) mentions
"notifications" exactly once, for **scroll** notifications (an unrelated
UI concept) — never once for OS/system notifications, in any release up
to 0.85.3.

Per the sprint brief's explicit instruction — "ne jamais réécrire un
système de notifications si Flet en fournit déjà un" (moot: it doesn't)
and "si aucune solution native propre n'existe : ne pas bricoler, créer
uniquement une abstraction prête à recevoir une future implémentation" —
this module does not bundle a third-party notification library (``plyer``,
``winotify``, ``notify-py``, D-Bus/``notify2``, ...) to paper over that
gap. Adding one is a real, deliberate decision (new dependency, new
per-platform packaging/permission concerns — see ``docs/PACKAGING.md``)
that belongs to whichever future sprint actually wires in real dispatch,
not to this one. What exists today is the seam: ``SystemNotifier`` (the
interface a future implementation fills in), ``NullSystemNotifier`` (the
only implementation shipped this sprint — always unavailable, by
construction, never a workaround), and ``notify_all`` (the one entry
point ``main_view.py`` calls — it never touches ``SystemNotifier`` itself).
"""

from __future__ import annotations

from collections.abc import Sequence
import sys
from typing import Protocol

from motorsport_calendar.gui.notification_service import Notification, NotificationKind
from motorsport_calendar.gui.strings import STRINGS
from motorsport_calendar.utils import get_logger

_logger = get_logger(__name__)

_KIND_LABELS: dict[NotificationKind, str] = {
    NotificationKind.WEEKEND_START: STRINGS.notification_kind_weekend_start,
    NotificationKind.FIRST_SESSION: STRINGS.notification_kind_first_session,
    NotificationKind.QUALIFYING: STRINGS.notification_kind_qualifying,
    NotificationKind.SPRINT: STRINGS.notification_kind_sprint,
    NotificationKind.RACE: STRINGS.notification_kind_race,
}


def _format(notification: Notification) -> tuple[str, str]:
    """Turn a structured ``Notification`` into (title, body) — the one
    place that formats notification text, so a future real notifier never
    has to (same "presentation concern lives outside the engine" split
    ``NotificationService``'s own docstring already calls for)."""
    kind_label = _KIND_LABELS[notification.kind]
    title = STRINGS.notification_title.format(kind=kind_label, event=notification.event_name)
    return title, notification.championship_name


class SystemNotifier(Protocol):
    """The seam a future sprint implements once a real notification
    backend exists (a Flet-provided service, or a deliberately chosen
    third-party library) — everything downstream of this module only
    ever depends on this shape, never on a concrete platform."""

    def is_available(self) -> bool:
        """True if this notifier can actually display a notification
        right now — checked once before attempting any ``notify()`` call,
        never assumed."""
        ...

    def notify(self, title: str, body: str) -> bool:
        """Attempt to show one OS notification. Returns whether it was
        actually shown. Must never raise — a failure is reported through
        the return value, exactly like ``is_available()`` reports
        unreadiness, per the brief's degradation rule."""
        ...


class NullSystemNotifier:
    """The only ``SystemNotifier`` this sprint ships — Flet has no OS
    notification API on any platform (see module docstring for the
    verified evidence), so there is nothing genuine to implement yet.
    Always unavailable, ``notify()`` always a no-op — never a crash,
    never a fabricated "success"."""

    def is_available(self) -> bool:
        return False

    def notify(self, title: str, body: str) -> bool:
        return False


def get_system_notifier() -> SystemNotifier:
    """The one place a future sprint would branch on ``sys.platform`` to
    return a real Windows/Linux/macOS-specific notifier. Today, always
    the null one — no platform detection is performed because there is
    nothing to detect *for* yet (see module docstring)."""
    return NullSystemNotifier()


def notify_all(
    notifications: Sequence[Notification], *, notifier: SystemNotifier | None = None
) -> int:
    """Attempt to display each of *notifications* as a real OS
    notification. Returns how many were actually shown.

    This function decides nothing about *what*/*when* to notify — that is
    entirely ``NotificationService.compute_notifications()``'s job,
    already done by the time *notifications* reaches here. It only
    decides *whether*/*how* to display what it's handed, and it never
    raises: an unavailable notifier, or one whose ``notify()`` misbehaves,
    degrades to doing nothing — the app must keep functioning normally
    either way (the brief's explicit "aucune erreur technique" rule).

    Args:
        notifications: already computed, already filtered/sorted by
            ``NotificationService`` — passed through unchanged.
        notifier: defaults to ``get_system_notifier()`` — overridable so
            tests (and, one day, a real implementation) never have to
            monkeypatch this module.
    """
    active = notifier if notifier is not None else get_system_notifier()

    try:
        available = active.is_available()
    except Exception:
        _logger.debug("System notifier availability check failed", exc_info=True)
        return 0

    if not available:
        _logger.debug(
            "System notifications unavailable (%s) — %d notification(s) not shown",
            sys.platform,
            len(notifications),
        )
        return 0

    shown = 0
    for notification in notifications:
        title, body = _format(notification)
        try:
            if active.notify(title, body):
                shown += 1
        except Exception:
            _logger.debug("System notifier raised on notify()", exc_info=True)
            continue
    return shown
