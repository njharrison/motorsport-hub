"""Tests for gui.notification_service — Sprint 46 notification engine.

No Flet dependency, no network: everything here builds an index directly
from ``Event``/``Session`` fixtures (the exact shape ``main_view.py``
already holds in ``year_events``) and asserts on the computed
``Notification`` tuples. Isolated from the real preferences file by the
autouse fixture in ``tests/conftest.py`` (``_isolated_gui_prefs``).
Covers every validation scenario from the brief (aucune/une/plusieurs
notifications, favoris uniquement, changement de fuseau horaire,
changement de saison) plus the 5 notification kinds and the 3 persisted
preferences.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from motorsport_calendar.gui.notification_service import (
    Notification,
    NotificationKind,
    NotificationService,
)
from motorsport_calendar.gui.preferences import load_preferences
from motorsport_calendar.models import (
    Championship,
    ChampionshipCategory,
    Circuit,
    Event,
    Session,
    SessionType,
)

_NOW = datetime(2026, 7, 12, 0, 0, tzinfo=UTC)


def _session(session_type: SessionType, start: datetime, *, hours: int = 1) -> Session:
    return Session(
        type=session_type,
        start_datetime=start,
        end_datetime=start + timedelta(hours=hours),
        title=session_type.value,
    )


def _event(
    *,
    championship_id: str = "formula1",
    name: str = "Belgian",
    sessions: tuple[Session, ...] = (),
    circuit_name: str = "Spa-Francorchamps",
    country: str = "Belgium",
    timezone: str = "UTC",
    event_uid: str | None = None,
) -> Event:
    championship = Championship(
        id=championship_id, name=championship_id, category=ChampionshipCategory.SINGLE_SEATER
    )
    circuit = Circuit(
        id=f"{circuit_name}-circuit",
        name=circuit_name,
        city=circuit_name,
        country=country,
        timezone=timezone,
    )
    return Event(
        championship=championship,
        season=2026,
        round=1,
        name=name,
        circuit=circuit,
        sessions=sessions,
        event_uid=event_uid or f"{championship_id}-{name}@test",
    )


class TestPreferencesDefaults:
    def test_disabled_by_default(self) -> None:
        assert NotificationService().enabled is False

    def test_default_lead_time_is_one_hour(self) -> None:
        assert NotificationService().default_lead_time == timedelta(hours=1)

    def test_not_favorites_only_by_default(self) -> None:
        assert NotificationService().favorites_only is False


class TestPreferencesPersistence:
    def test_set_enabled_persists(self) -> None:
        NotificationService().set_enabled(True)
        assert NotificationService().enabled is True

    def test_set_default_lead_time_persists(self) -> None:
        NotificationService().set_default_lead_time(15)
        assert NotificationService().default_lead_time == timedelta(minutes=15)

    def test_set_favorites_only_persists(self) -> None:
        NotificationService().set_favorites_only(True)
        assert NotificationService().favorites_only is True

    def test_uses_the_shared_preferences_file(self) -> None:
        NotificationService().set_enabled(True)
        prefs = load_preferences()
        assert prefs["notifications_enabled"] is True

    def test_does_not_clobber_other_preference_keys(self) -> None:
        from motorsport_calendar.gui.preferences import save_preferences

        save_preferences({**load_preferences(), "selected_championships": ["formula2"]})
        NotificationService().set_enabled(True)
        reloaded = load_preferences()
        assert reloaded["selected_championships"] == ["formula2"]
        assert reloaded["notifications_enabled"] is True


class TestNoNotifications:
    """ "aucune notification" validation scenario."""

    def test_empty_year_events(self) -> None:
        results = NotificationService().compute_notifications({}, now=_NOW)
        assert results == ()

    def test_event_with_no_sessions(self) -> None:
        event = _event(sessions=())
        results = NotificationService().compute_notifications({"formula1": [event]}, now=_NOW)
        assert results == ()

    def test_session_already_past_due(self) -> None:
        """A lead-time notification whose trigger instant has already
        passed is not "à venir" — excluded, even though the session
        itself is still in the future."""
        race = _session(SessionType.RACE, _NOW + timedelta(minutes=30))
        event = _event(sessions=(race,))
        results = NotificationService().compute_notifications(
            {"formula1": [event]}, now=_NOW, lead_times=(timedelta(hours=24),)
        )
        assert results == ()

    def test_session_entirely_in_the_past(self) -> None:
        race = _session(SessionType.RACE, _NOW - timedelta(days=1))
        event = _event(sessions=(race,))
        results = NotificationService().compute_notifications(
            {"formula1": [event]}, now=_NOW, lead_times=(timedelta(minutes=15),)
        )
        assert results == ()


class TestOneNotification:
    """ "une notification" validation scenario."""

    def test_single_session_single_lead_time_single_kind(self) -> None:
        race = _session(SessionType.RACE, _NOW + timedelta(days=2))
        event = _event(sessions=(race,))
        results = NotificationService().compute_notifications(
            {"formula1": [event]},
            now=_NOW,
            lead_times=(timedelta(hours=24),),
            kinds=(NotificationKind.RACE,),
        )
        assert len(results) == 1
        notification = results[0]
        assert isinstance(notification, Notification)
        assert notification.kind == NotificationKind.RACE
        assert notification.championship_id == "formula1"
        assert notification.championship_name == "Formula 1"
        assert notification.event_name == "Belgian Grand Prix"
        assert notification.session_start == race.start_datetime
        assert notification.lead_time == timedelta(hours=24)
        assert notification.trigger_at == race.start_datetime - timedelta(hours=24)


class TestMultipleNotifications:
    """ "plusieurs notifications" validation scenario."""

    def test_multiple_lead_times_produce_one_notification_each(self) -> None:
        race = _session(SessionType.RACE, _NOW + timedelta(days=2))
        event = _event(sessions=(race,))
        results = NotificationService().compute_notifications(
            {"formula1": [event]},
            now=_NOW,
            lead_times=(timedelta(hours=24), timedelta(hours=1), timedelta(minutes=15)),
            kinds=(NotificationKind.RACE,),
        )
        assert len(results) == 3
        assert {n.lead_time for n in results} == {
            timedelta(hours=24),
            timedelta(hours=1),
            timedelta(minutes=15),
        }

    def test_multiple_events_produce_multiple_notifications(self) -> None:
        race1 = _session(SessionType.RACE, _NOW + timedelta(days=2))
        race2 = _session(SessionType.RACE, _NOW + timedelta(days=9))
        event1 = _event(name="Belgian", sessions=(race1,), event_uid="e1@test")
        event2 = _event(name="Dutch", sessions=(race2,), event_uid="e2@test")
        results = NotificationService().compute_notifications(
            {"formula1": [event1, event2]},
            now=_NOW,
            lead_times=(timedelta(hours=24),),
            kinds=(NotificationKind.RACE,),
        )
        assert len(results) == 2
        assert {n.event_name for n in results} == {"Belgian Grand Prix", "Dutch Grand Prix"}

    def test_sorted_soonest_first(self) -> None:
        race_far = _session(SessionType.RACE, _NOW + timedelta(days=9))
        race_near = _session(SessionType.RACE, _NOW + timedelta(days=2))
        event_far = _event(name="Dutch", sessions=(race_far,), event_uid="far@test")
        event_near = _event(name="Belgian", sessions=(race_near,), event_uid="near@test")
        results = NotificationService().compute_notifications(
            {"formula1": [event_far, event_near]},
            now=_NOW,
            lead_times=(timedelta(hours=24),),
            kinds=(NotificationKind.RACE,),
        )
        assert [n.event_name for n in results] == ["Belgian Grand Prix", "Dutch Grand Prix"]


class TestNotificationKinds:
    def _weekend_event(self) -> tuple[Event, Session, Session, Session, Session]:
        fp1 = _session(SessionType.FP1, _NOW + timedelta(days=2))
        qualifying = _session(SessionType.QUALIFYING, _NOW + timedelta(days=3))
        sprint = _session(SessionType.SPRINT, _NOW + timedelta(days=3, hours=4))
        race = _session(SessionType.RACE, _NOW + timedelta(days=4))
        event = _event(sessions=(fp1, qualifying, sprint, race))
        return event, fp1, qualifying, sprint, race

    def test_weekend_start_and_first_session_both_anchor_on_the_earliest_session(self) -> None:
        event, fp1, _qualifying, _sprint, _race = self._weekend_event()
        results = NotificationService().compute_notifications(
            {"formula1": [event]},
            now=_NOW,
            lead_times=(timedelta(hours=1),),
            kinds=(NotificationKind.WEEKEND_START, NotificationKind.FIRST_SESSION),
        )
        assert len(results) == 2
        assert {n.session_start for n in results} == {fp1.start_datetime}
        assert {n.kind for n in results} == {
            NotificationKind.WEEKEND_START,
            NotificationKind.FIRST_SESSION,
        }

    def test_qualifying_anchors_on_the_qualifying_session_only(self) -> None:
        event, _fp1, qualifying, _sprint, _race = self._weekend_event()
        results = NotificationService().compute_notifications(
            {"formula1": [event]},
            now=_NOW,
            lead_times=(timedelta(hours=1),),
            kinds=(NotificationKind.QUALIFYING,),
        )
        assert len(results) == 1
        assert results[0].session_start == qualifying.start_datetime

    def test_sprint_anchors_on_the_sprint_session_only(self) -> None:
        event, _fp1, _qualifying, sprint, _race = self._weekend_event()
        results = NotificationService().compute_notifications(
            {"formula1": [event]},
            now=_NOW,
            lead_times=(timedelta(hours=1),),
            kinds=(NotificationKind.SPRINT,),
        )
        assert len(results) == 1
        assert results[0].session_start == sprint.start_datetime

    def test_race_anchors_on_the_race_session_only(self) -> None:
        event, _fp1, _qualifying, _sprint, race = self._weekend_event()
        results = NotificationService().compute_notifications(
            {"formula1": [event]},
            now=_NOW,
            lead_times=(timedelta(hours=1),),
            kinds=(NotificationKind.RACE,),
        )
        assert len(results) == 1
        assert results[0].session_start == race.start_datetime

    def test_event_without_a_sprint_produces_no_sprint_notification(self) -> None:
        race = _session(SessionType.RACE, _NOW + timedelta(days=2))
        event = _event(sessions=(race,))
        results = NotificationService().compute_notifications(
            {"formula1": [event]},
            now=_NOW,
            lead_times=(timedelta(hours=1),),
            kinds=(NotificationKind.SPRINT,),
        )
        assert results == ()

    def test_all_five_kinds_computed_by_default(self) -> None:
        event, *_ = self._weekend_event()
        results = NotificationService().compute_notifications(
            {"formula1": [event]}, now=_NOW, lead_times=(timedelta(hours=1),)
        )
        assert {n.kind for n in results} == set(NotificationKind)


class TestFavoritesOnly:
    """ "favoris uniquement" validation scenario."""

    def _year_events(self) -> dict[str, list[Event]]:
        race_f1 = _session(SessionType.RACE, _NOW + timedelta(days=2))
        race_motogp = _session(SessionType.RACE, _NOW + timedelta(days=3))
        return {
            "formula1": [_event(championship_id="formula1", sessions=(race_f1,))],
            "motogp": [
                _event(
                    championship_id="motogp",
                    name="Dutch",
                    sessions=(race_motogp,),
                    event_uid="motogp@test",
                )
            ],
        }

    def test_favorites_only_false_includes_every_championship(self) -> None:
        results = NotificationService().compute_notifications(
            self._year_events(),
            now=_NOW,
            lead_times=(timedelta(hours=1),),
            kinds=(NotificationKind.RACE,),
            favorites_only=False,
        )
        assert {n.championship_id for n in results} == {"formula1", "motogp"}

    def test_favorites_only_true_restricts_to_favorite_ids(self) -> None:
        results = NotificationService().compute_notifications(
            self._year_events(),
            now=_NOW,
            lead_times=(timedelta(hours=1),),
            kinds=(NotificationKind.RACE,),
            favorites_only=True,
            favorite_ids=frozenset({"motogp"}),
        )
        assert {n.championship_id for n in results} == {"motogp"}

    def test_favorites_only_true_with_no_favorites_yields_nothing(self) -> None:
        results = NotificationService().compute_notifications(
            self._year_events(),
            now=_NOW,
            lead_times=(timedelta(hours=1),),
            favorites_only=True,
            favorite_ids=frozenset(),
        )
        assert results == ()

    def test_persisted_favorites_only_preference_used_when_not_overridden(self) -> None:
        service = NotificationService()
        service.set_favorites_only(True)
        results = service.compute_notifications(
            self._year_events(),
            now=_NOW,
            lead_times=(timedelta(hours=1),),
            kinds=(NotificationKind.RACE,),
            favorite_ids=frozenset({"formula1"}),
        )
        assert {n.championship_id for n in results} == {"formula1"}


class TestTimezoneChange:
    """ "changement de fuseau horaire" validation scenario."""

    def test_non_utc_session_produces_the_same_result_as_its_utc_equivalent(self) -> None:
        # 2026-07-14 09:00 JST == 2026-07-14 00:00 UTC.
        tokyo_start = datetime(2026, 7, 14, 9, 0, tzinfo=ZoneInfo("Asia/Tokyo"))
        utc_start = datetime(2026, 7, 14, 0, 0, tzinfo=UTC)
        assert tokyo_start == utc_start  # sanity check on the fixture itself

        race = _session(SessionType.RACE, tokyo_start)
        event = _event(sessions=(race,), timezone="Asia/Tokyo")
        results = NotificationService().compute_notifications(
            {"formula1": [event]},
            now=_NOW,
            lead_times=(timedelta(hours=24),),
            kinds=(NotificationKind.RACE,),
        )
        assert len(results) == 1
        assert results[0].trigger_at == utc_start - timedelta(hours=24)

    def test_reference_now_in_a_different_timezone_still_filters_correctly(self) -> None:
        race = _session(SessionType.RACE, _NOW + timedelta(hours=2))
        event = _event(sessions=(race,))
        now_in_tokyo = _NOW.astimezone(ZoneInfo("Asia/Tokyo"))
        results = NotificationService().compute_notifications(
            {"formula1": [event]},
            now=now_in_tokyo,
            lead_times=(timedelta(hours=1),),
            kinds=(NotificationKind.RACE,),
        )
        assert len(results) == 1

    def test_session_far_from_utc_past_due_is_still_correctly_excluded(self) -> None:
        # A session 30 minutes from now (in a +09:00 zone) with a 24h lead
        # time must be excluded exactly like the UTC equivalent already
        # covered by TestNoNotifications — no double standard for
        # far-from-UTC circuits.
        near_start = (_NOW + timedelta(minutes=30)).astimezone(ZoneInfo("Asia/Tokyo"))
        race = _session(SessionType.RACE, near_start)
        event = _event(sessions=(race,), timezone="Asia/Tokyo")
        results = NotificationService().compute_notifications(
            {"formula1": [event]},
            now=_NOW,
            lead_times=(timedelta(hours=24),),
            kinds=(NotificationKind.RACE,),
        )
        assert results == ()


class TestSeasonChange:
    """ "changement de saison" validation scenario — no persisted index to
    go stale (unlike SearchService's index), each call is a fresh
    computation over whatever ``year_events`` it is given."""

    def test_different_year_events_yield_different_notifications(self) -> None:
        service = NotificationService()
        race_2026 = _session(SessionType.RACE, _NOW + timedelta(days=2))
        event_2026 = _event(name="Belgian", sessions=(race_2026,), event_uid="e2026@test")

        results_2026 = service.compute_notifications(
            {"formula1": [event_2026]},
            now=_NOW,
            lead_times=(timedelta(hours=1),),
            kinds=(NotificationKind.RACE,),
        )
        assert {n.event_name for n in results_2026} == {"Belgian Grand Prix"}

        race_2027 = _session(SessionType.RACE, _NOW + timedelta(days=400))
        event_2027 = _event(name="Dutch", sessions=(race_2027,), event_uid="e2027@test")

        results_2027 = service.compute_notifications(
            {"formula1": [event_2027]},
            now=_NOW,
            lead_times=(timedelta(hours=1),),
            kinds=(NotificationKind.RACE,),
        )
        assert {n.event_name for n in results_2027} == {"Dutch Grand Prix"}

    def test_switching_seasons_does_not_leak_the_previous_season_s_events(self) -> None:
        service = NotificationService()
        race_old = _session(SessionType.RACE, _NOW + timedelta(days=2))
        event_old = _event(name="Belgian", sessions=(race_old,), event_uid="old@test")
        service.compute_notifications(
            {"formula1": [event_old]}, now=_NOW, lead_times=(timedelta(hours=1),)
        )

        race_new = _session(SessionType.RACE, _NOW + timedelta(days=3))
        event_new = _event(name="Dutch", sessions=(race_new,), event_uid="new@test")
        results = service.compute_notifications(
            {"formula1": [event_new]},
            now=_NOW,
            lead_times=(timedelta(hours=1),),
            kinds=(NotificationKind.RACE,),
        )
        assert {n.event_name for n in results} == {"Dutch Grand Prix"}
