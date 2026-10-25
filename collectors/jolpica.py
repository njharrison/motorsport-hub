"""Jolpica Ergast-compatible F1 schedule, including session times when published."""
from datetime import datetime,timezone
import requests
from db import connect
KINDS=[('FirstPractice','FP1','practice'),('SecondPractice','FP2','practice'),('ThirdPractice','FP3','practice'),('SprintQualifying','Sprint Qualifying','qualifying'),('SprintShootout','Sprint Shootout','qualifying'),('Qualifying','Qualifying','qualifying'),('Sprint','Sprint','sprint')]
def collect(year):
 url=f'https://api.jolpi.ca/ergast/f1/{year}.json?limit=100'
 r=requests.get(url,timeout=30);r.raise_for_status();races=r.json()['MRData']['RaceTable']['Races'];count=0
 with connect() as c:
  for race in races:
   event_id=f'f1-{year}-{race["round"]}';source=race.get('url',url);now=datetime.now(timezone.utc).isoformat()
   c.execute('''INSERT INTO events(id,championship_id,name,venue,country,season,source_url,updated_at,subseries_id) VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET name=excluded.name,venue=excluded.venue,country=excluded.country,source_url=excluded.source_url,updated_at=excluded.updated_at,subseries_id=excluded.subseries_id''',(event_id,'f1',race['raceName'],race['Circuit']['circuitName'],race['Circuit']['Location']['country'],year,source,now,'f1'))
   for key,name,kind in KINDS+[('Race','Race','race')]:
    item={'date':race.get('date'),'time':race.get('time')} if key=='Race' else race.get(key)
    if not item or not item.get('date') or not item.get('time'):continue
    dt=datetime.fromisoformat((item['date']+'T'+item['time']).replace('Z','+00:00')).astimezone(timezone.utc).isoformat()
    c.execute('''INSERT INTO sessions(id,event_id,name,kind,start_utc,status,status_source,source_url,updated_at) VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET start_utc=excluded.start_utc,source_url=excluded.source_url,updated_at=excluded.updated_at''',(event_id+'-'+key.lower(),event_id,name,kind,dt,'scheduled','schedule',source,now));count+=1
 return count