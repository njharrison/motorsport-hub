"""Tests for gui.system_notifications — Sprint 56 native notification layer.

No Flet dependency, no real OS notification ever sent: ``NullSystemNotifier``
is the only ``SystemNotifier`` this sprint ships (Flet 0.85.3 has no OS
notification API on any platform — see the module's own docstring for the
verified evidence), so these tests exercise ``notify_all`` against both the
real default (``get_system_notifier()`` -> ``NullSystemNotifier``) and a
handful of stub ``SystemNotifier`` implementations to prove the dispatch
logic itself (available/unavailable, misbehaving notifiers, empty input)
without depending on any real platform.

Covers every validation scenario from the brief: notifications disponibles,
notifications indisponibles, moteur vide, absence de plateforme compatible.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from motorsport_calendar.gui.notification_service import Notification, NotificationKind
from motorsport_calendar.gui.strings import STRINGS
from motorsport_calendar.gui.system_notifications import (
    NullSystemNotifier,
    get_system_notifier,
    notify_all,
)


def _notification(
    *,
    kind: NotificationKind = NotificationKind.RACE,
    championship_name: str = "Formula 1",
    event_name: str = "Belgian Grand Prix",
) -> Notification:
    start = datetime(2026, 7, 12, 13, 0, tzinfo=UTC)
    return Notification(
        kind=kind,
        championship_id="formula1",
        championship_name=championship_name,
        event_name=event_name,
        session_start=start,
        lead_time=timedelta(minutes=60),
        trigger_at=start - timedelta(minutes=60),
    )


class _StubNotifier:
    """A fully-controllable ``SystemNotifier`` for exercising ``notify_all``
    without any real platform — records every call it receives."""

    def __init__(self, *, available: bool = True, notify_result: bool = True) -> None:
        self.available = available
        self.notify_result = notify_result
        self.calls: list[tuple[str, str]] = []

    def is_available(self) -> bool:
        return self.available

    def notify(self, title: str, body: str) -> bool:
        self.calls.append((title, body))
        return self.notify_result


class _RaisingOnAvailability:
    def is_available(self) -> bool:
        raise RuntimeError("boom")

    def notify(self, title: str, body: str) -> bool:
        raise AssertionError("must never be reached when is_available() raises")


class _RaisingOnNotify:
    def __init__(self) -> None:
        self.calls = 0

    def is_available(self) -> bool:
        return True

    def notify(self, title: str, body: str) -> bool:
        self.calls += 1
        raise RuntimeError("boom")


class TestNullSystemNotifier:
    """ "absence de plateforme compatible" — the only notifier this sprint
    ships, verified to always report unavailable and never crash."""

    def test_always_unavailable(self) -> None:
        assert NullSystemNotifier().is_available() is False

    def test_notify_always_returns_false(self) -> None:
        assert NullSystemNotifier().notify("title", "body") is False

    def test_notify_never_raises(self) -> None:
        notifier = NullSystemNotifier()
        for _ in range(3):
            notifier.notify("title", "body")  # must not raise


class TestGetSystemNotifier:
    def test_returns_a_null_notifier_today(self) -> None:
        """No platform is compatible yet (verified fact, see module
        docstring) — the factory always returns the null implementation."""
        assert isinstance(get_system_notifier(), NullSystemNotifier)

    def test_returns_a_fresh_instance_each_call(self) -> None:
        assert get_system_notifier() is not get_system_notifier()


class TestNotifyAllUnavailable:
    """ "notifications indisponibles" validation scenario."""

    def test_unavailable_notifier_returns_zero(self) -> None:
        notifier = _StubNotifier(available=False)
        assert notify_all((_notification(),), notifier=notifier) == 0

    def test_unavailable_notifier_never_calls_notify(self) -> None:
        notifier = _StubNotifier(available=False)
        notify_all((_notification(),), notifier=notifier)
        assert notifier.calls == []

    def test_default_notifier_is_unavailable(self) -> None:
        """ "absence de plateforme compatible" — with no override, the
        real default (NullSystemNotifier) is used and nothing is shown."""
        assert notify_all((_notification(),)) == 0


class TestNotifyAllAvailable:
    """ "notifications disponibles" validation scenario."""

    def test_available_notifier_dispatches_every_notification(self) -> None:
        notifier = _StubNotifier(available=True)
        notifications = (_notification(event_name="Belgian"), _notification(event_name="Dutch"))
        assert notify_all(notifications, notifier=notifier) == 2
        assert len(notifier.calls) == 2

    def test_dispatched_title_and_body_carry_the_right_information(self) -> None:
        notifier = _StubNotifier(available=True)
        notify_all(
            (_notification(kind=NotificationKind.RACE, event_name="Belgian Grand Prix"),),
            notifier=notifier,
        )
        title, body = notifier.calls[0]
        assert "Belgian Grand Prix" in title
        assert STRINGS.notification_kind_race in title
        assert body == "Formula 1"

    def test_notify_returning_false_is_not_counted_as_shown(self) -> None:
        notifier = _StubNotifier(available=True, notify_result=False)
        assert notify_all((_notification(),), notifier=notifier) == 0
        assert len(notifier.calls) == 1  # still attempted, just not counted


class TestNotifyAllEmptyEngine:
    """ "moteur vide" validation scenario — NotificationService produced
    nothing (e.g. no upcoming session)."""

    def test_empty_notifications_with_available_notifier_returns_zero(self) -> None:
        notifier = _StubNotifier(available=True)
        assert notify_all((), notifier=notifier) == 0
        assert notifier.calls == []

    def test_empty_notifications_with_unavailable_notifier_returns_zero(self) -> None:
        notifier = _StubNotifier(available=False)
        assert notify_all((), notifier=notifier) == 0


class TestNotifyAllDegradation:
    """The brief's explicit rule: never crash, never surface a technical
    error, keep functioning normally — for a misbehaving notifier."""

    def test_notifier_raising_on_is_available_never_crashes(self) -> None:
        assert notify_all((_notification(),), notifier=_RaisingOnAvailability()) == 0

    def test_notifier_raising_on_notify_never_crashes(self) -> None:
        notifier = _RaisingOnNotify()
        assert notify_all((_notification(), _notification()), notifier=notifier) == 0
        assert notifier.calls == 2  # both attempted despite each raising

    def test_one_notification_raising_does_not_block_the_next(self) -> None:
        class _FailFirstThenSucceed:
            def __init__(self) -> None:
                self.attempts = 0

            def is_available(self) -> bool:
                return True

            def notify(self, title: str, body: str) -> bool:
                self.attempts += 1
                if self.attempts == 1:
                    raise RuntimeError("boom")
                return True

        notifier = _FailFirstThenSucceed()
        assert notify_all((_notification(), _notification()), notifier=notifier) == 1
