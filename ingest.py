import argparse
from datetime import datetime,timezone
from db import init,connect
from collectors import jolpica,nascar,motocal,official
COLLECTORS={'f1':jolpica.collect,'nascar':nascar.collect,'indycar':lambda year:official.collect(year,'indycar'),'imsa':lambda year:official.collect(year,'imsa')}
COLLECTORS.update({name:(lambda year,p=name:motocal.collect(year,p)) for name in motocal.PROVIDERS})
# IndyCar and IMSA need verified sources; never silently label them imported.
PENDING={'motoe':'No verified collector yet','indy-nxt':'Session collector pending','imsa-support':'Support-series session collectors pending'}
def run(year,sources=None):
 init();success=True
 for source in sources or list(COLLECTORS):
  start=datetime.now(timezone.utc).isoformat()
  with connect() as c:run_id=c.execute('INSERT INTO source_runs(source,started_at,status) VALUES(?,?,?)',(source,start,'running')).lastrowid
  try:
   n=COLLECTORS[source](year);status='ok';msg=f'Imported {n} sessions for {year}'
  except Exception as exc:
   n=0;status='error';msg=f'{type(exc).__name__}: {exc}';success=False
  with connect() as c:c.execute('UPDATE source_runs SET finished_at=?,status=?,records=?,message=? WHERE id=?',(datetime.now(timezone.utc).isoformat(),status,n,msg,run_id))
  print(f'{source}: {status}: {msg}')
 return success
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--year',type=int,default=datetime.now().year);p.add_argument('--source',choices=list(COLLECTORS)+['all'],default='all');a=p.parse_args();raise SystemExit(0 if run(a.year,None if a.source=='all' else [a.source]) else 1)