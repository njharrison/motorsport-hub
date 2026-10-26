"""UK XMLTV guide ingestion. Programme entries are not marked confirmed for a session unless a matching event name is present."""
import gzip,io,re,urllib.request,xml.etree.ElementTree as ET
from datetime import datetime,timezone,timedelta
from difflib import SequenceMatcher
from db import connect,init_viewing
SOURCES=[
 ('EPGTalk','https://epgtalk.com/UK_guide.xml.gz'),
 ('Freeview','https://raw.githubusercontent.com/dp247/Freeview-EPG/master/epg.xml')]
CHANNELS={'sky sports f1','sky sports mix','sky sports main event','sky sports action','sky sports +','premier sports 1','premier sports 2','premier sports','channel 4','channel 4 hd','tnt sports 1','tnt sports 2','tnt sports 3','tnt sports 4','itv4'}
PATTERNS=[('nascar',r'\bnascar\b|\bcup series\b|daytona 500|talladega|brickyard 400'),('indycar',r'\bindycar\b|indy 500|indianapolis 500'),('f1',r'formula 1|\bf1\b|grand prix'),('motogp',r'\bmotogp\b'),('wec',r'world endurance|\bwec\b|le mans 24'),('imsa',r'\bimsa\b|weathertech'),('formula-e',r'formula e|formula-e')]
def dt(s):
 return datetime.strptime(s[:14],'%Y%m%d%H%M%S').replace(tzinfo=timezone(timedelta(hours=int(s[15:18])*(1 if s[14:15]=='+' else -1),minutes=int(s[18:20])*(1 if s[14:15]=='+' else -1)))).astimezone(timezone.utc).isoformat()
def normal(s):return re.sub(r'[^a-z0-9]+',' ',s.lower()).strip()
def stream(url):
 req=urllib.request.Request(url,headers={'User-Agent':'MotorsportHub/0.7 XMLTV reader'})
 response=urllib.request.urlopen(req,timeout=25)
 if url.endswith('.gz') or response.headers.get('Content-Encoding')=='gzip':
  return response,gzip.GzipFile(fileobj=response)
 return response,response
def programmes(url):
 response,source=stream(url)
 try:
  names={};selected=set();count=0
  parser=ET.iterparse(source,events=('start','end'))
  _,root=next(parser)
  for event,el in parser:
   if event!='end':continue
   if el.tag=='channel':
    cid=el.get('id');labels=[normal(x.text or '') for x in el.findall('display-name')]
    if any(any(target in label or label in target for target in CHANNELS if len(label)>5) for label in labels):
     selected.add(cid);names[cid]=next((x for x in labels if x),'')
    el.clear();root.clear()
   elif el.tag=='programme':
    if el.get('channel') in selected:
     yield names.get(el.get('channel'),el.get('channel')),el.get('start',''),el.get('stop',''),(el.findtext('title') or '').strip(),(el.findtext('desc') or '')[:180]
    el.clear();root.clear()
    count+=1
    if count>450000:break
 finally:
  source.close();response.close()
def collect():
 init_viewing();total=0;reports=[]
 now=datetime.now(timezone.utc);cutoff=(now-timedelta(days=1)).isoformat();end=(now+timedelta(days=15)).isoformat()
 with connect() as c:
  sessions=[dict(r) for r in c.execute("""SELECT s.id,s.name,s.start_utc,e.name event_name,e.championship_id FROM sessions s JOIN events e ON s.event_id=e.id WHERE s.start_utc BETWEEN ? AND ?""",(cutoff,end))]
 for provider,url in SOURCES:
  try:
   rows=[]
   for channel,raw_start,raw_stop,title,desc in programmes(url):
    content=normal(title+' '+desc[:180])
    series=next((key for key,pat in PATTERNS if re.search(pat,content)),None)
    if not series:continue
    try:start=dt(raw_start);stop=dt(raw_stop) if raw_stop else None
    except (ValueError,TypeError):continue
    if not cutoff<=start<=end:continue
    is_highlights=bool(re.search(r'highlights|replay|review|recap|repeat',content))
    kind='highlights' if is_highlights else 'live_unverified'
    match=None;match_status='unmatched'
    for s in sessions:
     if s['championship_id']!=series:continue
     event=normal(s['event_name'])
     event_tokens=[x for x in event.split() if len(x)>3 and x not in {'grand','prix','race','round','series','formula','championship'}]
     delta=abs((datetime.fromisoformat(start)-datetime.fromisoformat(s['start_utc'].replace('Z','+00:00'))).total_seconds())
     if event_tokens and any(x in content for x in event_tokens) and delta<36*3600:
      match=s['id'];match_status='candidate';break
    rows.append((match,series,'GB',provider,channel,'tv','free' if channel.startswith(('channel 4','itv4')) else 'subscription',start,stop,title,kind,url,now.isoformat(),match_status))
   with connect() as c:
    c.execute("DELETE FROM programme_listings WHERE provider=? AND source_url=?",(provider,url))
    c.executemany("""INSERT OR IGNORE INTO programme_listings(session_id,championship_id,country_code,provider,channel,platform_type,access_type,start_utc,end_utc,programme_title,broadcast_type,source_url,checked_at,match_status) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",rows)
   total+=len(rows);reports.append(f'{provider}: {len(rows)} relevant programmes, streamed XMLTV')
  except Exception as exc:reports.append(f'{provider}: ERROR {type(exc).__name__}: {exc}')
 print('EPG_IMPORT '+ ' | '.join(reports),flush=True)
 return {'programmes':total,'sources':reports}
if __name__=='__main__':print(collect())
