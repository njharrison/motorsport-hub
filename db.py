import os,sqlite3
from pathlib import Path
ROOT=Path(__file__).parent
DB=Path(os.environ.get('HUB_DB',str(ROOT/'hub.sqlite3')))
SERIES={'f1':('Formula 1','#ef4444'),'nascar':('NASCAR','#f59e0b'),'indycar':('IndyCar','#38bdf8'),'formula-e':('Formula E','#8b5cf6'),'motogp':('MotoGP','#22c55e'),'imsa':('IMSA','#f97316'),'wec':('WEC','#ec4899')}
SUBSERIES=[('f1','f1','F1',1),('f2','f1','Formula 2',0),('f3','f1','Formula 3',0),('f1-academy','f1','F1 Academy',0),('nascar-cup','nascar','Cup Series',1),('nascar-oap','nascar',"O’Reilly Auto Parts Series",0),('nascar-trucks','nascar','Craftsman Truck Series',0),('indycar-main','indycar','IndyCar Series',1),('indy-nxt','indycar','Indy NXT',0),('formula-e-main','formula-e','Formula E World Championship',1),('motogp-main','motogp','MotoGP',1),('moto2','motogp','Moto2',0),('moto3','motogp','Moto3',0),('motoe','motogp','MotoE',0),('imsa-weathertech','imsa','WeatherTech SportsCar Championship',1),('imsa-mpc','imsa','Michelin Pilot Challenge',0),('imsa-vp','imsa','VP Racing SportsCar Challenge',0),('wec-main','wec','FIA World Endurance Championship',1)]
DEFAULT_SUBSERIES=[s[0] for s in SUBSERIES if s[3]]
def connect():
 c=sqlite3.connect(DB);c.row_factory=sqlite3.Row;c.execute('PRAGMA foreign_keys=ON');return c
def init():
 with connect() as c:
  c.executescript((ROOT/'schema.sql').read_text())
  c.execute('CREATE TABLE IF NOT EXISTS event_windows(event_id TEXT PRIMARY KEY REFERENCES events(id) ON DELETE CASCADE,start_date TEXT NOT NULL,end_date TEXT NOT NULL,source_url TEXT,updated_at TEXT NOT NULL)')
  c.executemany('INSERT OR IGNORE INTO championships(id,name,color) VALUES(?,?,?)',[(k,*v) for k,v in SERIES.items()])
  c.execute('CREATE TABLE IF NOT EXISTS subseries (id TEXT PRIMARY KEY, championship_id TEXT NOT NULL REFERENCES championships(id), name TEXT NOT NULL, default_enabled INTEGER NOT NULL DEFAULT 0)')
  c.executemany('INSERT OR IGNORE INTO subseries(id,championship_id,name,default_enabled) VALUES(?,?,?,?)',SUBSERIES)
  columns=[x['name'] for x in c.execute('PRAGMA table_info(events)')]
  if 'subseries_id' not in columns:c.execute('ALTER TABLE events ADD COLUMN subseries_id TEXT REFERENCES subseries(id)')
  for championship,sub in [('f1','f1'),('nascar','nascar-cup'),('indycar','indycar-main'),('formula-e','formula-e-main'),('motogp','motogp-main'),('imsa','imsa-weathertech'),('wec','wec-main')]:
   c.execute('UPDATE events SET subseries_id=? WHERE championship_id=? AND subseries_id IS NULL',(sub,championship))
  columns=[x['name'] for x in c.execute('PRAGMA table_info(subscriptions)')]
  if 'subseries_csv' not in columns:c.execute('ALTER TABLE subscriptions ADD COLUMN subseries_csv TEXT')
def init_viewing():
 with connect() as c:
  c.execute("""CREATE TABLE IF NOT EXISTS viewing_options (
   id INTEGER PRIMARY KEY AUTOINCREMENT, championship_id TEXT NOT NULL,
   subseries_id TEXT, country_code TEXT NOT NULL, provider TEXT NOT NULL,
   platform_type TEXT NOT NULL, access_type TEXT NOT NULL, url TEXT,
   coverage_note TEXT, source_url TEXT, verified_at TEXT,
   UNIQUE(championship_id,subseries_id,country_code,provider,platform_type))""")
  c.execute("""CREATE TABLE IF NOT EXISTS programme_listings (
   id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT REFERENCES sessions(id),
   championship_id TEXT NOT NULL, country_code TEXT NOT NULL,
   provider TEXT NOT NULL, channel TEXT, platform_type TEXT NOT NULL,
   access_type TEXT NOT NULL, start_utc TEXT NOT NULL, end_utc TEXT,
   programme_title TEXT NOT NULL, broadcast_type TEXT NOT NULL,
   source_url TEXT NOT NULL, checked_at TEXT NOT NULL,
   match_status TEXT NOT NULL DEFAULT 'unmatched',
   UNIQUE(country_code,provider,programme_title,start_utc))""")
  c.execute("CREATE INDEX IF NOT EXISTS idx_programmes_session ON programme_listings(session_id)")
  options=[
   ('nascar','nascar-cup','GB','Premier Sports','tv','subscription','https://www.premiersports.com/','UK rights holder; exact channel varies by event','https://www.premiersports.com/'),
   ('nascar','nascar-cup','US','NASCAR US broadcast partners','tv_or_stream','subscription','https://www.nascar.com/news-media/2026/10/18/nascar-tv-guide/','FOX/FS1, Prime Video, TNT Sports, NBC/USA vary by race; US access restrictions apply','https://www.nascar.com/news-media/2026/10/18/nascar-tv-guide/'),
   ('indycar','indycar-main','GB','Sky Sports','tv','subscription','https://www.skysports.com/watch','Channel varies; check Sky Sports F1, Mix and other channels','https://www.indycar.com/news/2026/02/02-19-international-tv'),
   ('indycar','indycar-main','INT','INDYCAR LIVE','official_stream','varies','https://www.indycarlive.com/','Sessions and territory eligibility vary; verify access before watching','https://www.indycar.com/news/2026/02/02-19-international-tv'),
   ('f1','f1','GB','Sky Sports F1','tv','subscription','https://www.skysports.com/f1','Live sessions; exact programme airtimes require guide matching','https://www.skysports.com/f1'),
   ('f1','f1','GB','Channel 4','tv','free','https://www.channel4.com/','Highlights and selected live coverage; scheduled times unconfirmed','https://www.channel4.com/'),
   ('motogp','motogp-main','GB','TNT Sports','tv','subscription','https://www.tntsports.co.uk/','Live coverage; confirm session-specific airtimes','https://www.tntsports.co.uk/'),
   ('wec','wec-main','GB','TNT Sports','tv','subscription','https://www.tntsports.co.uk/','Live coverage; confirm race-specific airtimes','https://www.tntsports.co.uk/'),
   ('imsa','imsa-weathertech','INT','IMSA TV','official_stream','free','https://www.imsa.com/tvlive/','Availability subject to local rights and event coverage','https://www.imsa.com/tvlive/')
  ]
  c.executemany("""INSERT OR IGNORE INTO viewing_options
   (championship_id,subseries_id,country_code,provider,platform_type,access_type,url,coverage_note,source_url)
   VALUES(?,?,?,?,?,?,?,?,?)""",options)
