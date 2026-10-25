"""Import supported series from the MIT-licensed motorsport-calendar CLI.
Install with: pip install motorsport-calendar icalendar
"""
import subprocess,sys,tempfile,os
from pathlib import Path
from datetime import datetime,timezone
from db import connect

PROVIDERS={
 'f2':('f1','f2','f2'), 'f3':('f1','f3','f3'),
 'f1-academy':('f1','f1-academy','f1-academy'),
 'formula-e':('formula-e','formula-e-main','formula-e'),
 'wec':('wec','wec-main','wec'),
 'motogp':('motogp','motogp-main','motogp'),
 'moto2':('motogp','moto2','moto2'),
 'moto3':('motogp','moto3','moto3'),
}
def to_utc(dt):
 if not isinstance(dt,datetime):raise ValueError('Event has no time of day')
 if dt.tzinfo is None:raise ValueError('Naive event time')
 return dt.astimezone(timezone.utc).isoformat()
def collect(year,provider):
 from icalendar import Calendar
 if provider not in PROVIDERS:raise ValueError('Unknown provider '+provider)
 championship,subseries,command=PROVIDERS[provider]
 with tempfile.TemporaryDirectory() as tmp:
  path=Path(tmp)/'schedule.ics'
  env=os.environ.copy();env.update(PYTHONIOENCODING='utf-8',PYTHONUTF8='1')
  result=subprocess.run([sys.executable,'-m','motorsport_calendar',f'generate-{command}',str(year),str(path)],capture_output=True,text=True,encoding="utf-8",errors="replace",env=env,timeout=120)
  if result.returncode or not path.exists():raise RuntimeError((result.stderr or result.stdout or 'No calendar produced')[-700:])
  cal=Calendar.from_ical(path.read_bytes())
  items=[]
  for component in cal.walk('VEVENT'):
   try:start=to_utc(component.decoded('DTSTART'))
   except (ValueError,KeyError):continue
   title=str(component.get('SUMMARY','Session'))
   uid=str(component.get('UID',f'{provider}-{start}-{title}'))
   location=str(component.get('LOCATION',''))
   end=None
   if component.get('DTEND'):
    try:end=to_utc(component.decoded('DTEND'))
    except ValueError:pass
   lower=title.lower()
   kind='qualifying' if 'qualif' in lower or 'shootout' in lower else 'practice' if 'practice' in lower or 'fp' in lower else 'sprint' if 'sprint' in lower else 'warmup' if 'warm' in lower else 'race'
   items.append((uid,title,location,start,end,kind))
  if not items:raise ValueError(f'{provider}: source returned no timed sessions for {year}')
  now=datetime.now(timezone.utc).isoformat()
  with connect() as db:
   for uid,title,location,start,end,kind in items:
    # Stable upstream UID avoids duplicate events across refreshes.
    import hashlib
    ident=hashlib.sha256((provider+'|'+uid).encode()).hexdigest()[:24]
    event_id=f'motocal-{provider}-{ident}'
    db.execute('''INSERT INTO events(id,championship_id,name,venue,season,source_url,updated_at,subseries_id) VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET name=excluded.name,venue=excluded.venue,updated_at=excluded.updated_at''',(event_id,championship,title,location,year,'https://github.com/naviss29/motorsport-calendar',now,subseries))
    db.execute('''INSERT INTO sessions(id,event_id,name,kind,start_utc,end_utc,source_url,updated_at) VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET name=excluded.name,kind=excluded.kind,start_utc=excluded.start_utc,end_utc=excluded.end_utc,updated_at=excluded.updated_at''',(event_id+'-session',event_id,title,kind,start,end,'https://github.com/naviss29/motorsport-calendar',now))
  return len(items)