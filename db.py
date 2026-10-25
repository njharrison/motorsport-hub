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