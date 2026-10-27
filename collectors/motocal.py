"""Import supported series from the MIT-licensed motorsport-calendar CLI.
Install with: pip install motorsport-calendar icalendar
"""
import subprocess,sys,tempfile,os,re,hashlib
from collections import defaultdict
from pathlib import Path
from datetime import datetime,timezone,timedelta
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
  # One-off diagnostic: inspect unmodified upstream WEC VEVENT properties.
  # Logged before the importer extracts or rewrites any fields.
  if provider=='wec':
   import json
   for n,component in enumerate(cal.walk('VEVENT')):
    if n>=6:break
    fields={}
    for key in component.keys():
     value=component.get(key)
     if isinstance(value,list):fields[str(key)]=[str(v)[:400] for v in value]
     else:fields[str(key)]=str(value)[:400]
    print('WEC_RAW_VEVENT '+json.dumps({'index':n,'properties':fields},ensure_ascii=False),flush=True)
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
   kind='qualifying' if 'qualif' in lower or 'hyperpole' in lower or 'shootout' in lower else 'practice' if 'practice' in lower or 'fp' in lower else 'sprint' if 'sprint' in lower else 'warmup' if 'warm' in lower else 'race'
   items.append((uid,title,location,start,end,kind))
  if not items:raise ValueError(f'{provider}: source returned no timed sessions for {year}')
  # The upstream ICS has one UID per SESSION, not per race weekend.
  # Group by venue and the nearest race session (within 4 days), preserving
  # separate MotoGP/Moto2/Moto3 weekends as independent subseries.
  def clean_name(title):
   name=re.sub(r'(?i)\\b(free practice [1-4]|practice [1-4]?|fp[1-4]|qualifying [12]?|qualifying|hyperpole|q[12]|sprint race|sprint|warm.?up|race|shootout)\\b',' ',title)
   name=re.sub(r'(?i)\\b(motogp|moto2|moto3|formula 2|formula 3|formula e|fia wec|wec)\\b',' ',name)
   return re.sub(r'\\s+',' ',name).strip(' -–—:|,')
  groups=defaultdict(list)
  for item in items:
   uid,title,location,start,end,kind=item
   d=datetime.fromisoformat(start)
   # Friday-Monday sessions belong to the same race weekend.
   anchor=(d-timedelta(days=d.weekday())).date().isoformat()
   candidate=clean_name(title)
   venue=location.strip().lower()
   key=(venue or candidate.lower(),anchor)
   groups[key].append(item)
  now=datetime.now(timezone.utc).isoformat()
  with connect() as db:
   for (venue_key,anchor),group in groups.items():
    race=next((x for x in group if x[5]=='race' and 'sprint' not in x[1].lower()),group[-1])
    race_name=clean_name(race[1])
    candidates=[clean_name(x[1]) for x in group]
    event_name=max((x for x in candidates if x),key=len,default='')
    # Prefer the race's name, but don't allow generic "Race" to hide the GP.
    if race_name and (provider=='wec' or len(race_name)>len(event_name)//2):event_name=race_name
    if provider=='wec':
     # The ICS exporter may reduce an official event to a bare "Race".
     # Prefer the event's circuit/location over a session-type label.
     wec_names={
      'qatar':'1812 km of Qatar','lusail':'1812 km of Qatar',
      'imola':'6 Hours of Imola','spa':'6 Hours of Spa-Francorchamps',
      'le mans':'24 Hours of Le Mans','sarthe':'24 Hours of Le Mans',
      'interlagos':'6 Hours of São Paulo','sao paulo':'6 Hours of São Paulo',
      'austin':'Lone Star Le Mans','cota':'Lone Star Le Mans','circuit of the americas':'Lone Star Le Mans',
      'fuji':'6 Hours of Fuji','bahrain':'8 Hours of Bahrain','sakhir':'8 Hours of Bahrain'}
     evidence=' '.join([venue_key]+[x[1]+' '+x[2] for x in group]).lower()
     official_name=next((name for token,name in wec_names.items() if token in evidence),None)
     if official_name:event_name=official_name
     elif event_name.lower() in {'race','hyperpole','qualifying','practice','free practice','warm up','warm-up'}:
      event_name=(location or venue_key).strip()+' WEC'
    if not event_name or event_name.lower() in {'grand prix','gp','main'}:
     event_name=next((x[2] for x in group if x[2]),'Unknown event')
    if not re.search(r'(?i)grand prix|\\bgp\\b|prix|round|eprix|24 hours|6 hours|8 hours',event_name):
     if provider in {'motogp','moto2','moto3'}:event_name+=' Grand Prix'
    ident=hashlib.sha256((provider+'|'+venue_key+'|'+anchor).encode()).hexdigest()[:24]
    event_id=f'motocal-{provider}-weekend-{ident}'
    location=race[2]
    db.execute('''INSERT INTO events(id,championship_id,name,venue,season,source_url,updated_at,subseries_id)
     VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET name=excluded.name,venue=excluded.venue,updated_at=excluded.updated_at''',
     (event_id,championship,event_name,location,year,'https://github.com/naviss29/motorsport-calendar',now,subseries))
    for uid,title,location,start,end,kind in group:
     sid='motocal-'+provider+'-'+hashlib.sha256((provider+'|'+uid).encode()).hexdigest()[:24]+'-session'
     session_name=re.sub(r'(?i)^.*?\\b(free practice [1-4]|practice [1-4]?|fp[1-4]|qualifying [12]?|qualifying|q[12]|sprint race|sprint|warm.?up|race|shootout)\\b.*$',r'\\1',title).strip()
     if provider=='wec' and 'hyperpole' in title.lower():session_name='Hyperpole'
     if not session_name or session_name==title:session_name=title
     db.execute('''INSERT INTO sessions(id,event_id,name,kind,start_utc,end_utc,source_url,updated_at)
      VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET event_id=excluded.event_id,name=excluded.name,kind=excluded.kind,start_utc=excluded.start_utc,end_utc=excluded.end_utc,updated_at=excluded.updated_at''',
      (sid,event_id,session_name,kind,start,end,'https://github.com/naviss29/motorsport-calendar',now))
   # Old per-session events are now orphaned; remove only these legacy records.
   db.execute("""DELETE FROM events WHERE id LIKE ? AND season=? AND id NOT IN (SELECT event_id FROM sessions)""",(f'motocal-{provider}-%',year))
  return len(items)
