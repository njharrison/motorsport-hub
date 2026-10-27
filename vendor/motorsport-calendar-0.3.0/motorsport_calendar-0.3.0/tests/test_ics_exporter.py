"""Tests for IcsExporter."""

from datetime import timedelta
from pathlib import Path

from icalendar import Calendar
import pytest

from motorsport_calendar.exporters.ics import IcsExporter
from motorsport_calendar.models import (
    Championship,
    Circuit,
    Event,
    Session,
    SessionType,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse(data: bytes) -> Calendar:
    return Calendar.from_ical(data)


def _vevents(cal: Calendar) -> list:
    return [c for c in cal.walk() if c.name == "VEVENT"]


# ---------------------------------------------------------------------------
# File generation
# ---------------------------------------------------------------------------


class TestExportIsPackagingSafe:
    """Sprint 49 — export must work for any user-supplied output path,
    with zero dependency on the current working directory or the Git
    repository being present (a packaged executable may run from anywhere,
    with no repo on disk at all)."""

    def test_export_works_far_from_any_repo_path(
        self, tmp_path: Path, australian_gp: Event
    ) -> None:
        """A path with no relation whatsoever to this project's own
        directory tree — mirrors where a real packaged app would write."""
        output = tmp_path / "far" / "away" / "nested" / "calendar.ics"
        output.parent.mkdir(parents=True)
        IcsExporter().export([australian_gp], output)
        assert output.exists()
        assert output.stat().st_size > 0

    def test_export_does_not_read_or_write_relative_to_cwd(
        self, tmp_path: Path, australian_gp: Event, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Launching the app from an arbitrary directory (e.g. a packaged
        executable's own install folder) must not affect where an
        absolute, user-supplied output path resolves to."""
        other_cwd = tmp_path / "not_the_output_dir"
        other_cwd.mkdir()
        monkeypatch.chdir(other_cwd)

        output = tmp_path / "elsewhere" / "calendar.ics"
        output.parent.mkdir()
        IcsExporter().export([australian_gp], output)

        assert output.exists()
        assert list(other_cwd.iterdir()) == []  # nothing written into the CWD

    def test_export_accepts_an_absolute_path(self, tmp_path: Path, australian_gp: Event) -> None:
        output = (tmp_path / "calendar.ics").resolve()
        assert output.is_absolute()
        IcsExporter().export([australian_gp], output)
        assert output.exists()


class TestExportFile:
    def test_creates_file(self, tmp_path: Path, australian_gp: Event) -> None:
        output = tmp_path / "calendar.ics"
        IcsExporter().export([australian_gp], output)
        assert output.exists()
        assert output.stat().st_size > 0

    def test_file_starts_with_vcalendar(self, tmp_path: Path, australian_gp: Event) -> None:
        output = tmp_path / "calendar.ics"
        IcsExporter().export([australian_gp], output)
        assert output.read_bytes().startswith(b"BEGIN:VCALENDAR")

    def test_export_to_string_is_valid_ics(self, australian_gp: Event) -> None:
        result = IcsExporter().export_to_string([australian_gp])
        assert "BEGIN:VCALENDAR" in result
        assert "BEGIN:VEVENT" in result
        assert "END:VEVENT" in result
        assert "END:VCALENDAR" in result


# ---------------------------------------------------------------------------
# VEVENT count
# ---------------------------------------------------------------------------


class TestVEventCount:
    def test_two_sessions_produce_two_vevents(self, tmp_path: Path, australian_gp: Event) -> None:
        # australian_gp has qualifying + race = 2 sessions
        output = tmp_path / "calendar.ics"
        IcsExporter().export([australian_gp], output)
        cal = _parse(output.read_bytes())
        assert len(_vevents(cal)) == 2

    def test_empty_event_list_produces_no_vevents(self, tmp_path: Path) -> None:
        output = tmp_path / "empty.ics"
        IcsExporter().export([], output)
        cal = _parse(output.read_bytes())
        assert _vevents(cal) == []

    def test_event_without_sessions_produces_no_vevents(
        self, tmp_path: Path, f1: Championship, albert_park: Circuit
    ) -> None:
        event = Event(
            championship=f1,
            season=2025,
            round=99,
            name="No Sessions GP",
            circuit=albert_park,
            event_uid="f1-2025-99-test@motorsport-calendar",
        )
        output = tmp_path / "no_sessions.ics"
        IcsExporter().export([event], output)
        cal = _parse(output.read_bytes())
        assert _vevents(cal) == []

    def test_multiple_events_accumulate_vevents(
        self,
        tmp_path: Path,
        australian_gp: Event,
        f1: Championship,
        albert_park: Circuit,
        race_session: Session,
    ) -> None:
        second_event = Event(
            championship=f1,
            season=2025,
            round=2,
            name="Bahrain Grand Prix",
            circuit=albert_park,
            event_uid="f1-2025-02-bhr@motorsport-calendar",
            sessions=(race_session,),
        )
        output = tmp_path / "multi.ics"
        IcsExporter().export([australian_gp, second_event], output)
        cal = _parse(output.read_bytes())
        # 2 sessions (aus) + 1 session (bhr) = 3
        assert len(_vevents(cal)) == 3


# ---------------------------------------------------------------------------
# UID uniqueness and format
# ---------------------------------------------------------------------------


class TestUid:
    def test_uids_are_unique(self, tmp_path: Path, australian_gp: Event) -> None:
        output = tmp_path / "calendar.ics"
        IcsExporter().export([australian_gp], output)
        cal = _parse(output.read_bytes())
        uids = [str(c.get("uid")) for c in _vevents(cal)]
        assert len(uids) == len(set(uids))

    def test_uid_format_is_event_uid_dash_session_type(
        self, tmp_path: Path, australian_gp: Event
    ) -> None:
        output = tmp_path / "calendar.ics"
        IcsExporter().export([australian_gp], output)
        cal = _parse(output.read_bytes())
        uids = {str(c.get("uid")) for c in _vevents(cal)}
        assert f"{australian_gp.event_uid}-{SessionType.QUALIFYING}" in uids
        assert f"{australian_gp.event_uid}-{SessionType.RACE}" in uids


# ---------------------------------------------------------------------------
# Timezone preservation
# ---------------------------------------------------------------------------


class TestTimezone:
    def test_dtstart_is_timezone_aware(self, tmp_path: Path, australian_gp: Event) -> None:
        output = tmp_path / "calendar.ics"
        IcsExporter().export([australian_gp], output)
        cal = _parse(output.read_bytes())
        for vevent in _vevents(cal):
            dtstart = vevent.get("dtstart").dt
            assert dtstart.tzinfo is not None, "DTSTART must be timezone-aware"

    def test_dtend_is_timezone_aware(self, tmp_path: Path, australian_gp: Event) -> None:
        output = tmp_path / "calendar.ics"
        IcsExporter().export([australian_gp], output)
        cal = _parse(output.read_bytes())
        for vevent in _vevents(cal):
            dtend = vevent.get("dtend").dt
            assert dtend.tzinfo is not None, "DTEND must be timezone-aware"

    def test_utc_datetime_serialises_as_plain_z_suffix_no_tzid(
        self, tmp_path: Path, australian_gp: Event
    ) -> None:
        """MC-002 P0-1 regression guard: this project's convention is that
        every provider normalises session times to UTC before they reach
        this exporter (see AcoSportsEventSource._parse_datetime and
        PulseliveBase._parse_datetime). As long as that holds, DTSTART/DTEND
        must serialise as a bare Z-suffixed UTC value with no TZID
        parameter and the calendar must carry no VTIMEZONE component — a
        fixed-offset, non-UTC, non-IANA tzinfo reaching this exporter would
        instead produce an invalid synthetic TZID (the actual bug found in
        MC-001, since fixed for the ACO series at the source)."""
        output = tmp_path / "calendar.ics"
        IcsExporter().export([australian_gp], output)
        raw_bytes = output.read_bytes()
        raw = raw_bytes.decode()
        assert "TZID=" not in raw
        assert "BEGIN:VTIMEZONE" not in raw
        for vevent in _vevents(_parse(raw_bytes)):
            assert vevent.get("dtstart").dt.utcoffset() == timedelta(0)
            assert vevent.get("dtend").dt.utcoffset() == timedelta(0)


# ---------------------------------------------------------------------------
# Field values
# ---------------------------------------------------------------------------


class TestFieldValues:
    def test_summary_matches_session_title(self, tmp_path: Path, australian_gp: Event) -> None:
        output = tmp_path / "calendar.ics"
        IcsExporter().export([australian_gp], output)
        cal = _parse(output.read_bytes())
        summaries = {str(c.get("summary")) for c in _vevents(cal)}
        assert "Australian Grand Prix — Race" in summaries
        assert "Australian Grand Prix — Qualifying" in summaries

    def test_description_included_when_present(self, tmp_path: Path, australian_gp: Event) -> None:
        output = tmp_path / "calendar.ics"
        IcsExporter().export([australian_gp], output)
        cal = _parse(output.read_bytes())
        # race_session has description; qualifying_session does not
        descriptions = [str(c.get("description")) for c in _vevents(cal) if c.get("description")]
        assert any("Round 1 of the 2025 season." in d for d in descriptions)

    def test_description_absent_when_none(self, tmp_path: Path, australian_gp: Event) -> None:
        output = tmp_path / "calendar.ics"
        IcsExporter().export([australian_gp], output)
        cal = _parse(output.read_bytes())
        # qualifying_session has no description → its VEVENT has no DESCRIPTION property
        qualifying = next(c for c in _vevents(cal) if "Qualifying" in str(c.get("summary")))
        assert qualifying.get("description") is None

    def test_location_is_circuit_name_and_country(
        self, tmp_path: Path, australian_gp: Event
    ) -> None:
        output = tmp_path / "calendar.ics"
        IcsExporter().export([australian_gp], output)
        cal = _parse(output.read_bytes())
        expected = f"{australian_gp.circuit.name}, {australian_gp.circuit.country}"
        for vevent in _vevents(cal):
            assert str(vevent.get("location")) == expected

    def test_status_is_confirmed(self, tmp_path: Path, australian_gp: Event) -> None:
        output = tmp_path / "calendar.ics"
        IcsExporter().export([australian_gp], output)
        cal = _parse(output.read_bytes())
        for vevent in _vevents(cal):
            assert str(vevent.get("status")).upper() == "CONFIRMED"

    def test_prodid_contains_motorsport_calendar(
        self, tmp_path: Path, australian_gp: Event
    ) -> None:
        output = tmp_path / "calendar.ics"
        IcsExporter().export([australian_gp], output)
        cal = _parse(output.read_bytes())
        prodid = str(cal.get("prodid"))
        assert "Motorsport Calendar" in prodid


# ---------------------------------------------------------------------------
# VALARM — rappel configurable
# ---------------------------------------------------------------------------


def _valarms(cal: Calendar) -> list:
    return [c for c in cal.walk() if c.name == "VALARM"]


class TestValarm:
    def test_no_alarm_by_default(self, tmp_path: Path, australian_gp: Event) -> None:
        output = tmp_path / "no_alarm.ics"
        IcsExporter().export([australian_gp], output)
        cal = _parse(output.read_bytes())
        assert _valarms(cal) == []

    def test_no_alarm_when_alarm_minutes_is_zero(
        self, tmp_path: Path, australian_gp: Event
    ) -> None:
        output = tmp_path / "alarm0.ics"
        IcsExporter(alarm_minutes=0).export([australian_gp], output)
        cal = _parse(output.read_bytes())
        assert _valarms(cal) == []

    def test_alarm_present_when_alarm_minutes_gt_zero(
        self, tmp_path: Path, australian_gp: Event
    ) -> None:
        output = tmp_path / "alarm30.ics"
        IcsExporter(alarm_minutes=30).export([australian_gp], output)
        cal = _parse(output.read_bytes())
        assert len(_valarms(cal)) > 0

    def test_one_alarm_per_session(self, tmp_path: Path, australian_gp: Event) -> None:
        # australian_gp has 2 sessions → 2 VALARMs
        output = tmp_path / "alarm.ics"
        IcsExporter(alarm_minutes=15).export([australian_gp], output)
        cal = _parse(output.read_bytes())
        assert len(_valarms(cal)) == len(australian_gp.sessions)

    def test_alarm_trigger_is_negative_offset(self, tmp_path: Path, australian_gp: Event) -> None:
        output = tmp_path / "alarm.ics"
        IcsExporter(alarm_minutes=30).export([australian_gp], output)
        content = output.read_text(encoding="utf-8")
        assert "TRIGGER:-PT30M" in content

    def test_alarm_action_is_display(self, tmp_path: Path, australian_gp: Event) -> None:
        output = tmp_path / "alarm.ics"
        IcsExporter(alarm_minutes=30).export([australian_gp], output)
        cal = _parse(output.read_bytes())
        for alarm in _valarms(cal):
            assert str(alarm.get("action")).upper() == "DISPLAY"

    def test_export_to_string_contains_valarm(self, australian_gp: Event) -> None:
        content = IcsExporter(alarm_minutes=30).export_to_string([australian_gp])
        assert "BEGIN:VALARM" in content
        assert "END:VALARM" in content
