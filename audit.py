"""Read-only calendar data audit."""
from db import init, connect
init()
with connect() as c:
    print('Sessions by championship / subseries:')
    for r in c.execute('SELECT e.championship_id,e.subseries_id,count(*) n FROM sessions s JOIN events e ON e.id=s.event_id GROUP BY 1,2 ORDER BY 1,2'):
        print(dict(r))
    print('\nNASCAR session kinds:')
    for r in c.execute("SELECT s.kind,count(*) n FROM sessions s JOIN events e ON e.id=s.event_id WHERE e.championship_id='nascar' GROUP BY s.kind ORDER BY s.kind"):
        print(dict(r))
    print('\nNASCAR sessions outside their event season:')
    for r in c.execute("SELECT s.id,s.start_utc,e.season FROM sessions s JOIN events e ON e.id=s.event_id WHERE e.championship_id='nascar' AND substr(s.start_utc,1,4)!=CAST(e.season AS TEXT) LIMIT 20"):
        print(dict(r))
    print('\nSame start and kind (review only; not necessarily duplicates):')
    for r in c.execute('''SELECT e.subseries_id,s.start_utc,s.kind,count(*) n,group_concat(s.name,' | ') names
      FROM sessions s JOIN events e ON e.id=s.event_id GROUP BY 1,2,3 HAVING count(*)>1 ORDER BY n DESC LIMIT 25'''):
        print(dict(r))