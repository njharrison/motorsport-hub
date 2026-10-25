"""Conservative official 2026 calendar seeds. Never invent a start time."""
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
from db import connect

INDY=[('03-01','Streets of St. Petersburg','12:00'),('03-07','Phoenix Raceway','15:00'),('03-15','Streets of Arlington',None),('03-29','Barber Motorsports Park','13:00'),('04-19','Streets of Long Beach','17:30'),('05-09','Indianapolis Motor Speedway Road Course','16:30'),('05-24','Indianapolis 500',None),('05-31','Streets of Detroit','12:30'),('06-07','World Wide Technology Raceway','21:00'),('06-21','Road America','14:00'),('07-05','Mid-Ohio Sports Car Course','12:30'),('07-19','Nashville Superspeedway',None),('08-09','Portland International Raceway','16:00'),('08-16','Streets of Markham','12:00'),('08-23','Streets of Washington DC',None),('08-29','Milwaukee Mile Race 1','14:30'),('08-30','Milwaukee Mile Race 2','13:00'),('09-06','WeatherTech Raceway Laguna Seca','14:30')]
IMSA=[('01-16','01-18','Roar Before The Rolex 24','Daytona International Speedway'),('01-21','01-25','Rolex 24 At Daytona','Daytona International Speedway'),('03-18','03-21','Twelve Hours of Sebring','Sebring International Raceway'),('04-17','04-19','Long Beach','Long Beach Street Circuit'),('05-01','05-03','Laguna Seca','WeatherTech Raceway Laguna Seca'),('05-29','05-30','Detroit Sports Car Classic','Detroit Street Circuit'),('06-25','06-28','Six Hours of The Glen','Watkins Glen'),('07-10','07-12','Canadian Tire Motorsport Park','Canadian Tire Motorsport Park'),('07-30','08-02','Road America','Road America'),('08-21','08-23','Michelin GT Challenge at VIR','Virginia International Raceway'),('09-18','09-20','Battle on the Bricks','Indianapolis Motor Speedway'),('09-30','10-03','Petit Le Mans','Michelin Raceway Road Atlanta')]
def collect(year,provider):
 if year!=2026: return 0 # no invented future seasons
 now=datetime.now(timezone.utc).isoformat()
 with connect() as db:
  if provider=='indycar':
   for day,name,time in INDY:
    eid='official-indycar-2026-'+day+'-'+name.lower().replace(' ','-')
    start='2026-'+day;end=start
    db.execute('''INSERT INTO events(id,championship_id,name,venue,season,source_url,updated_at,subseries_id) VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET name=excluded.name,updated_at=excluded.updated_at''',(eid,'indycar',name,name,year,'https://www.indycar.com/schedule/?year=2026',now,'indycar-main'))
    db.execute('''INSERT INTO event_windows(event_id,start_date,end_date,source_url,updated_at) VALUES(?,?,?,?,?) ON CONFLICT(event_id) DO UPDATE SET start_date=excluded.start_date,end_date=excluded.end_date,updated_at=excluded.updated_at''',(eid,start,end,'https://www.indycar.com/schedule/?year=2026',now))
    if time:
     local=datetime.fromisoformat(start+'T'+time).replace(tzinfo=ZoneInfo('America/New_York'))
     utc=local.astimezone(timezone.utc).isoformat()
     db.execute('''INSERT INTO sessions(id,event_id,name,kind,start_utc,source_url,updated_at) VALUES(?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET start_utc=excluded.start_utc,updated_at=excluded.updated_at''',(eid+'-race',eid,'Race (published start time)','race',utc,'https://www.indycar.com/schedule/?year=2026',now))
   return len(INDY)
  if provider=='imsa':
   for start,end,name,venue in IMSA:
    eid='official-imsa-2026-'+start
    db.execute('''INSERT INTO events(id,championship_id,name,venue,season,source_url,updated_at,subseries_id) VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET name=excluded.name,updated_at=excluded.updated_at''',(eid,'imsa',name,venue,year,'https://www.imsa.com/weathertech/weathertech-2026-schedule/',now,'imsa-weathertech'))
    db.execute('''INSERT INTO event_windows(event_id,start_date,end_date,source_url,updated_at) VALUES(?,?,?,?,?) ON CONFLICT(event_id) DO UPDATE SET start_date=excluded.start_date,end_date=excluded.end_date,updated_at=excluded.updated_at''',(eid,'2026-'+start,'2026-'+end,'https://www.imsa.com/weathertech/weathertech-2026-schedule/',now))
   return len(IMSA)
 raise ValueError(provider)