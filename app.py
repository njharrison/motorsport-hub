import csv,io,os,secrets
from datetime import datetime,timezone,timedelta
from pathlib import Path
from fastapi import FastAPI,HTTPException,Query
from fastapi.responses import HTMLResponse,Response,FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from db import init,connect,SERIES,SUBSERIES,DEFAULT_SUBSERIES,ROOT
init()
app=FastAPI(title='Motorsport Hub',version='0.4.0')
app.mount('/static',StaticFiles(directory=ROOT/'static'),name='static')
@app.get('/')
def home():return FileResponse(ROOT/'static'/'index.html')
@app.get('/api/series')
def series():return [{'id':k,'name':v[0],'color':v[1]} for k,v in SERIES.items()]
@app.get('/api/subseries')
def subseries():return [{'id':sid,'championship_id':champ,'name':name,'default_enabled':bool(default)} for sid,champ,name,default in SUBSERIES]
@app.get('/api/sessions')
def sessions(start:str|None=None,end:str|None=None,series:str='',subseries:str|None=None,limit:int=Query(500,ge=1,le=2000)):
 now=datetime.now(timezone.utc)
 start=start or (now-timedelta(days=1)).isoformat();end=end or (now+timedelta(days=90)).isoformat()
 ids=[x for x in series.split(',') if x in SERIES]
 sql='''SELECT s.*,e.name AS event_name,e.venue,e.country,e.championship_id,e.subseries_id,e.source_url AS event_url,c.name AS championship_name,c.color FROM sessions s JOIN events e ON e.id=s.event_id JOIN championships c ON c.id=e.championship_id WHERE s.start_utc>=? AND s.start_utc<=?'''
 args=[start,end]
 if ids:sql+=' AND e.championship_id IN ('+','.join('?' for _ in ids)+')';args+=ids
 if subseries is not None:
  subids=[x for x in subseries.split(',') if x in {r[0] for r in SUBSERIES}]
  if not subids:return []
  sql+=' AND e.subseries_id IN ('+','.join('?' for _ in subids)+')';args+=subids
 sql+=' ORDER BY s.start_utc LIMIT ?';args.append(limit)
 with connect() as c:return [dict(x) for x in c.execute(sql,args).fetchall()]
@app.get('/api/coverage')
def coverage():
 with connect() as c:
  counts={x['championship_id']:x['n'] for x in c.execute('SELECT e.championship_id,COUNT(*) AS n FROM sessions s JOIN events e ON e.id=s.event_id GROUP BY e.championship_id')}
  runs=[dict(x) for x in c.execute('''SELECT r.* FROM source_runs r JOIN (SELECT source,MAX(id) id FROM source_runs GROUP BY source) latest ON latest.id=r.id ORDER BY r.source''')]
  last_success={r['source']:r['finished_at'] for r in c.execute("SELECT source,MAX(finished_at) AS finished_at FROM source_runs WHERE status='ok' GROUP BY source")}
 return {'series':[{'id':k,'name':v[0],'sessions':counts.get(k,0)} for k,v in SERIES.items()],'source_runs':runs,'last_success':last_success,'pending_sources':{'motoe':'Collector pending','indy-nxt':'Session collector pending','imsa-support':'Support-series collector pending'},'live_timing_connected':False}
@app.get('/api/broadcast')
def broadcast(country:str='GB'):
 with connect() as c:return [dict(x) for x in c.execute('SELECT * FROM broadcast WHERE country_code=? ORDER BY championship_id',(country.upper(),))]
class Subscription(BaseModel):
 series:list[str]
 subseries:list[str]|None=None
 kinds:list[str]=['race','qualifying','practice','sprint','warmup']
@app.post('/api/subscriptions')
def create_subscription(body:Subscription):
 ids=[s for s in body.series if s in SERIES]
 if not ids:raise HTTPException(400,'Choose at least one championship')
 token=secrets.token_urlsafe(24);key=secrets.token_hex(12)
 with connect() as c:
  c.execute('INSERT INTO subscriptions(id,token,series_csv,kinds_csv,created_at) VALUES(?,?,?,?,?)',(key,token,','.join(ids),','.join(body.kinds),datetime.now(timezone.utc).isoformat()))
  c.execute('UPDATE subscriptions SET subseries_csv=? WHERE id=?',(','.join(x for x in (body.subseries if body.subseries is not None else DEFAULT_SUBSERIES) if x in {r[0] for r in SUBSERIES}),key))
 return {'feed_path':f'/calendar/{token}.ics','note':'Keep this feed URL private; anyone with it can view your selected events.'}
def escape_ics(s):return str(s or '').replace('\\','\\\\').replace(';','\\;').replace(',','\\,').replace('\n','\\n')
def dt_ics(s):return datetime.fromisoformat(s.replace('Z','+00:00')).astimezone(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
def ics_rows(rows):
 lines=['BEGIN:VCALENDAR','VERSION:2.0','PRODID:-//Motorsport Hub//EN','CALSCALE:GREGORIAN','METHOD:PUBLISH','X-WR-CALNAME:Motorsport Hub']
 for r in rows:
  lines+=['BEGIN:VEVENT','UID:'+r['id']+'@motorsport-hub','DTSTAMP:'+dt_ics(r['updated_at']),'DTSTART:'+dt_ics(r['start_utc']),'SUMMARY:'+escape_ics(r['championship_name']+' | '+r['event_name']+' | '+r['name']),'LOCATION:'+escape_ics(r['venue']),'DESCRIPTION:'+escape_ics(r['source_url'] or r['event_url'] or ''),'STATUS:'+('CANCELLED' if r['status']=='cancelled' else 'CONFIRMED')]
  if r['end_utc']:lines.append('DTEND:'+dt_ics(r['end_utc']))
  lines.append('END:VEVENT')
 lines.append('END:VCALENDAR')
 return '\r\n'.join(lines)+'\r\n'
@app.get('/calendar/{token}.ics')
def calendar(token:str):
 with connect() as c:
  sub=c.execute('SELECT * FROM subscriptions WHERE token=?',(token,)).fetchone()
  if not sub:raise HTTPException(404,'Calendar not found')
  ids=sub['series_csv'].split(',');kinds=sub['kinds_csv'].split(',');subs=(sub['subseries_csv'] or '').split(',')
  sql='''SELECT s.*,e.name AS event_name,e.venue,e.source_url AS event_url,c.name AS championship_name FROM sessions s JOIN events e ON e.id=s.event_id JOIN championships c ON c.id=e.championship_id WHERE e.championship_id IN ('''+','.join('?' for _ in ids)+')'
  args=list(ids)
  if sub['subseries_csv'] is not None:
   subs=[x for x in subs if x in {r[0] for r in SUBSERIES}]
   if not subs:return Response(ics_rows([]),media_type='text/calendar; charset=utf-8')
   sql+=' AND e.subseries_id IN ('+','.join('?' for _ in subs)+')';args+=subs
  if kinds:sql+=' AND s.kind IN ('+','.join('?' for _ in kinds)+')';args+=kinds
  rows=[dict(r) for r in c.execute(sql,args)]
 return Response(ics_rows(rows),media_type='text/calendar; charset=utf-8',headers={'Content-Disposition':'inline; filename="motorsport-hub.ics"','Cache-Control':'public, max-age=900'})

@app.get('/api/event-windows')
def event_windows(start:str|None=None,end:str|None=None,subseries:str|None=None):
 now=datetime.now(timezone.utc).date().isoformat()
 start=(start or now)[:10];end=(end or (datetime.now(timezone.utc)+timedelta(days=90)).date().isoformat())[:10]
 sql="""SELECT w.*,e.name AS event_name,e.venue,e.championship_id,e.subseries_id,c.name AS championship_name,c.color FROM event_windows w JOIN events e ON e.id=w.event_id JOIN championships c ON c.id=e.championship_id WHERE w.start_date<=? AND w.end_date>=?"""
 args=[end,start]
 if subseries is not None:
  subs=[x for x in subseries.split(',') if x in {r[0] for r in SUBSERIES}]
  if not subs:return []
  sql+=' AND e.subseries_id IN ('+','.join('?' for _ in subs)+')';args+=subs
 sql+=' ORDER BY w.start_date'
 with connect() as c:return [dict(r) for r in c.execute(sql,args)]