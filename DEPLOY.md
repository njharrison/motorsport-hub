# Railway deployment

1. Push this folder to a GitHub repository (do not commit hub.sqlite3).
2. In Railway choose **New Project → Deploy from GitHub repo**.
3. Add a persistent volume mounted at `/data`. Set environment variable `HUB_DB=/data/hub.sqlite3`.
4. Set `PYTHONUTF8=1` and `PYTHONIOENCODING=utf-8`. Railway supplies `PORT`.
5. Deploy; open the generated Railway domain and verify `/api/series`.
6. Populate the persistent database using Railway's service shell / CLI, running `python ingest.py --year 2026` and `python ingest.py --year 2027`. Some future feeds may be unpublished; check source status.
7. Schedule a recurring Railway cron service (separate service, same mounted database) or an external job to run ingestion. Do not rely on the web process to import on boot.

**Important:** Railway services may not share a mounted volume simultaneously; if a cron service cannot mount the same volume, use a single service with an external scheduler hitting a secured import endpoint, or migrate to managed Postgres before scheduling. The current SQLite version is intended for one web process. Calendar subscription tokens are stored in SQLite and will be lost without a persistent volume.

For a quick demo you can deploy without a volume, but the database will be empty and reset on redeploy.