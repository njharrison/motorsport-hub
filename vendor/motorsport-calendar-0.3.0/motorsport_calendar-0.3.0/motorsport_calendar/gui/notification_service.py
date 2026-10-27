"""NotificationService — computes upcoming session/weekend notifications
from data already loaded in memory (Sprint 46).

Foundations only: no OS notification (Windows/Linux/macOS) is sent by this
module — that is explicitly out of scope for this sprint. This service
only *computes* a structured, display-agnostic list of notifications that
a future platform-specific layer can turn into a real system notification
without ever touching this file again (no Flet import, no I/O beyond the
already-existing preferences file — same "usable standalone" contract as
``FavoritesService``).

No network calls, ever: the caller (eventually ``main_view.py``, not
wired this sprint) passes in ``year_events`` — the exact same dict
``controller.get_calendar_year_events`` already produces and
``search_service.py``/``season_explorer.py`` already consume — never a
fresh provider scan.

Reuses existing models end-to-end rather than inventing a second
normalization: ``display_names.get_display_name`` for championship names,
``event_display.normalize_event_display`` (Sprint 32, ADR-023) for event
names — a notification's event name is never worded differently than the
same event everywhere else in the app.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum

from motorsport_calendar.gui.display_names import get_display_name
from motorsport_calendar.gui.event_display import normalize_event_display
from motorsport_calendar.gui.preferences import load_preferences, save_preferences
from motorsport_calendar.models import Event, Session, SessionType


class NotificationKind(StrEnum):
    """The 5 notification kinds required by the brief.

    ``WEEKEND_START`` and ``FIRST_SESSION`` both currently anchor on the
    same instant — an event's earliest session — since the domain model
    has no separate concept of "weekend start" distinct from "first
    session" (see ADR-037). Kept as two distinct kinds anyway (not
    collapsed into one) because the brief explicitly lists them
    separately and a future sprint may need to distinguish them (e.g. a
    series with a preview/test day ahead of its first timed session).
    """

    WEEKEND_START = "WEEKEND_START"
    FIRST_SESSION = "FIRST_SESSION"
    QUALIFYING = "QUALIFYING"
    SPRINT = "SPRINT"
    RACE = "RACE"


# Kinds anchored on a specific SessionType — WEEKEND_START/FIRST_SESSION are
# handled separately (anchored on the earliest session, any type).
_KIND_SESSION_TYPES: dict[NotificationKind, SessionType] = {
    NotificationKind.QUALIFYING: SessionType.QUALIFYING,
    NotificationKind.SPRINT: SessionType.SPRINT,
    NotificationKind.RACE: SessionType.RACE,
}


@dataclass(frozen=True)
class Notification:
    """One computed, display-agnostic notification.

    Purely structured data — no formatted message string. Formatting is a
    presentation concern for whichever future consumer (a GUI list, a
    Windows/Linux/macOS system notification) turns this into text; this
    service stays usable by all of them without modification.
    """

    kind: NotificationKind
    championship_id: str
    championship_name: str
    event_name: str
    session_start: datetime
    lead_time: timedelta
    trigger_at: datetime


def _earliest_session(sessions: tuple[Session, ...]) -> Session | None:
    return min(sessions, key=lambda s: s.start_datetime) if sessions else None


def _anchor_sessions(event: Event, kind: NotificationKind) -> list[Session]:
    """Which session(s) of *event* anchor a notification of this *kind*.

    WEEKEND_START/FIRST_SESSION: the single earliest session (any type),
    or none if the event has no sessions at all. QUALIFYING/SPRINT/RACE:
    every session matching that exact ``SessionType`` — usually 0 or 1,
    never assumed to be exactly 1 (an event legitimately has no sprint).
    """
    if kind in (NotificationKind.WEEKEND_START, NotificationKind.FIRST_SESSION):
        earliest = _earliest_session(event.sessions)
        return [earliest] if earliest is not None else []
    session_type = _KIND_SESSION_TYPES[kind]
    return [s for s in event.sessions if s.type == session_type]


class NotificationService:
    """Computes upcoming notifications; owns the 3 persisted preferences
    the brief asks for ("notifications activées", "délai par défaut",
    "favoris uniquement").

    Mirrors ``FavoritesService``'s own "service holds state, built fresh,
    persisted on the shared preferences file, read-modify-write on every
    save" pattern (Sprint 44) — no second config file, no Flet
    dependency, constructed fresh wherever needed rather than a shared
    singleton.
    """

    def __init__(self) -> None:
        prefs = load_preferences()
        self._enabled: bool = bool(prefs.get("notifications_enabled", False))
        self._default_lead_time_minutes: int = int(
            prefs.get("notifications_default_lead_time_minutes", 60)
        )
        self._favorites_only: bool = bool(prefs.get("notifications_favorites_only", False))

    @property
    def enabled(self) -> bool:
        """True if the notification engine is turned on."""
        return self._enabled

    @property
    def default_lead_time(self) -> timedelta:
        """Default delay before a session at which a notification fires."""
        return timedelta(minutes=self._default_lead_time_minutes)

    @property
    def favorites_only(self) -> bool:
        """True if notifications are restricted to favorited championships."""
        return self._favorites_only

    def set_enabled(self, value: bool) -> None:
        """Persist whether the notification engine is turned on."""
        self._enabled = value
        self._save("notifications_enabled", value)

    def set_default_lead_time(self, minutes: int) -> None:
        """Persist the default delay (in minutes) before a session."""
        self._default_lead_time_minutes = minutes
        self._save("notifications_default_lead_time_minutes", minutes)

    def set_favorites_only(self, value: bool) -> None:
        """Persist whether notifications are restricted to favorites."""
        self._favorites_only = value
        self._save("notifications_favorites_only", value)

    def _save(self, key: str, value: bool | int) -> None:
        prefs = load_preferences()
        prefs[key] = value
        save_preferences(prefs)

    def compute_notifications(
        self,
        year_events: dict[str, list[Event]],
        *,
        now: datetime,
        lead_times: Sequence[timedelta] | None = None,
        kinds: Sequence[NotificationKind] | None = None,
        favorites_only: bool | None = None,
        favorite_ids: frozenset[str] = frozenset(),
    ) -> tuple[Notification, ...]:
        """Every notification not yet due, across *year_events* (already
        fetched — never a network call here).

        Args:
            year_events: registry championship id -> its events for the
                currently loaded year (``controller.get_calendar_year_events``
                — the same dict "Mon calendrier"/"Recherche" already use).
            now: reference instant — required, never read from the wall
                clock internally (same convention as
                ``upcoming_weekend.find_upcoming_weekend``), so this stays
                deterministic and fully unit-testable.
            lead_times: how long before each anchor session to notify —
                e.g. ``(timedelta(hours=24), timedelta(minutes=15))``
                produces one notification per lead time per anchor
                session. ``None`` (default) uses ``[self.default_lead_time]``
                — the single persisted "délai par défaut".
            kinds: which of the 5 ``NotificationKind`` to compute. ``None``
                (default) computes all 5 — the brief requires the engine
                be *capable* of producing all of them, not that every
                caller always wants all of them (a future preferences UI
                may let a user opt out of some kinds, same spirit as
                *lead_times*).
            favorites_only: ``None`` (default) uses the persisted
                ``self.favorites_only`` preference; pass an explicit
                ``True``/``False`` to override it for one call without
                touching the persisted preference (e.g. for tests).
            favorite_ids: championship ids considered "favorite" when
                *favorites_only* resolves to ``True``. Ignored otherwise.

        Returns:
            Notifications whose ``trigger_at`` is still in the future
            (``>= now``) — "à venir" per the brief, never a past-due
            notification — sorted soonest-first, ties broken by
            championship name, event name, then kind (deterministic
            output for identical input).
        """
        resolved_lead_times = (
            tuple(lead_times) if lead_times is not None else (self.default_lead_time,)
        )
        resolved_kinds = tuple(kinds) if kinds is not None else tuple(NotificationKind)
        resolved_favorites_only = self.favorites_only if favorites_only is None else favorites_only

        results: list[Notification] = []
        for championship_id, events in year_events.items():
            if resolved_favorites_only and championship_id not in favorite_ids:
                continue
            championship_name = get_display_name(championship_id)
            for event in events:
                display = normalize_event_display(championship_id, event)
                for kind in resolved_kinds:
                    for session in _anchor_sessions(event, kind):
                        for lead_time in resolved_lead_times:
                            trigger_at = session.start_datetime - lead_time
                            if trigger_at < now:
                                continue
                            results.append(
                                Notification(
                                    kind=kind,
                                    championship_id=championship_id,
                                    championship_name=championship_name,
                                    event_name=display.grand_prix_name,
                                    session_start=session.start_datetime,
                                    lead_time=lead_time,
                                    trigger_at=trigger_at,
                                )
                            )

        results.sort(
            key=lambda n: (
                n.trigger_at,
                n.championship_name.casefold(),
                n.event_name.casefold(),
                n.kind,
            )
        )
        return tuple(results)
