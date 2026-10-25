"""NASCAR schedule cache. Only sporting sessions enter the public calendar.

Refreshes reconcile one successfully fetched season at a time. Never remove data
if a source fails, is empty, or has an unexpected shape.
"""
from datetime import datetime, timezone
import requests
from db import connect

IDS = {1: 'nascar-cup', 2: 'nascar-oap', 3: 'nascar-trucks'}
KINDS = {1: 'practice', 2: 'qualifying', 3: 'race'}


def utc(value, *, declared_utc=False):
    if not value:
        return None
    dt = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    if dt.tzinfo is None:
        if declared_utc:
            # NASCAR's *_utc fields sometimes omit an explicit +00:00 suffix.
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            # Do not guess a circuit timezone for a local timestamp.
            return None
    return dt.astimezone(timezone.utc).isoformat()


def parse_races(data, sid, year):
    races = data.get(f'series_{sid}', data.get('races', data.get('race_list', []))) if isinstance(data, dict) else data
    if not isinstance(races, list) or not races:
        raise ValueError(f'Empty or unexpected NASCAR schedule for series {sid}, {year}')
    return races


def prepare(races, year, sid):
    events, sessions = {}, {}
    for race in races:
        rid = race.get('race_id') or race.get('race_num')
        if rid is None:
            continue
        eid = f'nascar-{year}-{sid}-{rid}'
        name = race.get('race_name') or race.get('name') or f'Race {rid}'
        venue = str(race.get('track_name') or race.get('track') or '')
        schedule = race.get('schedule') or race.get('weekend_schedule') or race.get('race_schedule') or []
        if not isinstance(schedule, list):
            raise ValueError(f'Unexpected weekend schedule for {eid}')
        if not schedule:
            schedule = [{'event_name': 'Race', 'run_type': 3, 'start_time_utc': race.get('race_date') or race.get('date_scheduled')}]
        for i, item in enumerate(schedule):
            try:
                run_type = int(item.get('run_type'))
            except (TypeError, ValueError):
                continue
            kind = KINDS.get(run_type)
            if not kind:
                continue
            raw_utc = item.get('start_time_utc')
            start = utc(raw_utc, declared_utc=True) if raw_utc else utc(item.get('start_time'))
            if not start or datetime.fromisoformat(start).year != year:
                continue
            raw_end_utc = item.get('end_time_utc')
            end = utc(raw_end_utc, declared_utc=True) if raw_end_utc else utc(item.get('end_time'))
            session_id = f'{eid}-{kind}-{i}'
            sessions[session_id] = (eid, str(item.get('event_name') or kind.title()), kind, start, end)
            events[eid] = (name, venue)
    if not sessions:
        raise ValueError(f'No NASCAR sporting sessions found for {sid} in {year}; refusing reconciliation')
    return events, sessions


def reconcile(year, sid, events, sessions):
    """Atomic upsert + removal of obsolete sessions for a single series/season."""
    now = datetime.now(timezone.utc).isoformat()
    subseries = IDS[sid]
    with connect() as db:
        # Restrict cleanup to this collector's event IDs and year, not all NASCAR data.
        prefix = f'nascar-{year}-{sid}-%'
        for eid, (name, venue) in events.items():
            db.execute('''INSERT INTO events(id,championship_id,name,venue,season,source_url,updated_at,subseries_id)
              VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET name=excluded.name,
              venue=excluded.venue,updated_at=excluded.updated_at''',
              (eid, 'nascar', name, venue, year, 'https://www.nascar.com/schedule/', now, subseries))
        for session_id, (eid, name, kind, start, end) in sessions.items():
            db.execute('''INSERT INTO sessions(id,event_id,name,kind,start_utc,end_utc,source_url,updated_at)
              VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET name=excluded.name,
              kind=excluded.kind,start_utc=excluded.start_utc,end_utc=excluded.end_utc,updated_at=excluded.updated_at''',
              (session_id, eid, name, kind, start, end, 'https://www.nascar.com/schedule/', now))
        # SQLite temporary table avoids parameter-count limits and keeps the operation atomic.
        db.execute('CREATE TEMP TABLE IF NOT EXISTS current_nascar_ids (id TEXT PRIMARY KEY)')
        db.execute('DELETE FROM current_nascar_ids')
        db.executemany('INSERT INTO current_nascar_ids(id) VALUES(?)', [(x,) for x in sessions])
        db.execute('''DELETE FROM sessions WHERE event_id IN
          (SELECT id FROM events WHERE id LIKE ? AND championship_id='nascar' AND subseries_id=? AND season=?)
          AND id NOT IN (SELECT id FROM current_nascar_ids)''', (prefix, subseries, year))
        db.execute('''DELETE FROM events WHERE id LIKE ? AND championship_id='nascar'
          AND subseries_id=? AND season=? AND id NOT IN
          (SELECT DISTINCT event_id FROM sessions) AND id NOT IN
          (SELECT event_id FROM event_windows)''', (prefix, subseries, year))
    return len(sessions)


def collect(year):
    total = 0
    with requests.Session() as http:
        for sid in IDS:
            url = f'https://cf.nascar.com/cacher/{year}/' + ('1/' if sid == 1 else '') + 'race_list_basic.json'
            response = http.get(url, timeout=30)
            if response.status_code in (403, 404) and year > datetime.now(timezone.utc).year:
                print(f'  NASCAR {IDS[sid]} {year}: schedule unavailable ({response.status_code}); existing data retained')
                continue
            response.raise_for_status()
            events, sessions = prepare(parse_races(response.json(), sid, year), year, sid)
            total += reconcile(year, sid, events, sessions)
    return total