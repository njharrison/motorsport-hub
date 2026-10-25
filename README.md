# Motorsport Hub v0.1

Responsive motorsport schedule viewer and calendar subscription server for **F1, NASCAR, IndyCar, Formula E, MotoGP, IMSA and WEC**.

## Run locally (Windows, macOS or Linux)

Requires Python 3.10+.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python ingest.py --year 2026
python ingest.py --year 2027
uvicorn app:app --reload
```

Open http://127.0.0.1:8000 . The app also runs with an empty database if an ingestion source is unavailable. There are **no invented demo races**.

## Actual data coverage

- **F1**: Jolpica race calendar collector implemented. Includes race start times only. Jolpica's availability and historical/current coverage depend on the upstream service. This collector does **not** import practice, sprint, or qualifying.
- **NASCAR, IndyCar, Formula E, MotoGP, IMSA, WEC**: schema, filters, event/session views, and calendar feeds are implemented; **data ingestion connectors are not yet implemented**. The UI reports zero records until real data is added.
- **Live status**: only `scheduled` and explicit imported statuses; no timing feed connected, so no false “live” claims.
- **Reminders**: subscribe via iCalendar and configure alerts in your calendar client. Direct push notifications and a background reminder dispatcher are **not implemented**.
- **Where to watch**: country-specific broadcast database and UI are implemented; **no UK broadcasters have been verified or populated**. Add verified data using SQL when available.

## API

- `GET /api/series` — supported championships
- `GET /api/sessions?start=...&end=...&series=f1,nascar` — sessions in UTC
- `GET /api/coverage` — records per championship and collector health
- `GET /api/broadcast?country=GB` — verified broadcasters only
- `POST /api/subscriptions` — `{ "series": ["f1", "wec"], "kinds": ["race"] }`
- `GET /calendar/{token}.ics` — private, dynamically generated subscription feed

## Next development steps

1. Build and test collectors for the six other championships, preferably official published feeds with attribution, backoff, validation and change detection.
2. Add full F1 weekend session schedules using a verified session-level provider.
3. Add a background job for hourly schedule refresh and persist source provenance/changes.
4. Verify UK broadcasting rights per championship and populate the `broadcast` table.
5. Implement user accounts, web push opt-in, a reminder worker, and a separate trusted live-status feed.
6. Add tests for schedule changes, cancellation, timezone shifts and calendar compatibility.

## Deployment

Works on Railway with start command `uvicorn app:app --host 0.0.0.0 --port $PORT`. SQLite must be stored on a persistent volume: set `HUB_DB=/data/hub.sqlite3` and mount `/data`. For multiple app instances or heavier usage, migrate to PostgreSQL. Do not run with an ephemeral SQLite database in production.

## Attribution

Jolpica F1 API: https://api.jolpi.ca/ . Data remains subject to the upstream provider's terms and availability.

## v0.2 — series selection and ingestion

- All 18 listed headline/support series exist in the data model; only the seven headline series are enabled initially. Series selections persist in the browser and are used by calendar subscriptions.
- The F1 Jolpica collector now imports published practice, qualifying, sprint and race session times.
- NASCAR's documented weekend schedule endpoint is supported for Cup, O'Reilly Auto Parts and Trucks. The endpoint's availability and response shape must be verified on your network.
- Other championship collectors are **not yet implemented**; selecting those series does not fabricate sessions.
- `python ingest.py --year 2026 --source f1` imports only F1; `--source nascar` imports NASCAR; omitting `--source` attempts both.
- The local database is `hub.sqlite3`. Existing v0.1 data is migrated in place. Stop the server before replacing application files, and keep a backup of your database.
- Launch alongside Daytona: `uvicorn app:app --reload --port 8001`.

## v0.4 — official schedule seeds and validation

- `python ingest.py --year 2026`: includes 2026 IndyCar race dates and 2026 IMSA WeatherTech event weekends. IndyCar only adds a timed session when a published time is available; IMSA event windows are date-only until official session timing is ingested. The calendar displays these windows separately and **does not** create calendar subscription reminders from date-only windows.
- `python audit.py`: reports NASCAR classification counts and potential duplicates without modifying the database. Review its findings before any automatic deletion.
- Windows CLI calendar collector now forces UTF-8 encoding for subprocess output.
- Unpublished seasons are not fabricated for IndyCar or IMSA. The 2027 NASCAR endpoint may still return HTTP 403; previously imported data remains intact.
- This is an initial seed, not a continuously synchronised live IndyCar or IMSA feed. Reconfirm published start times before using push notifications.

Install over v0.3 while **keeping your existing hub.sqlite3**. The ZIP intentionally does not include a database file.


## v0.5.1 NASCAR timezone fix

NASCAR occasionally emits ISO timestamps without offsets in fields explicitly named
`start_time_utc` and `end_time_utc`. These are now interpreted as UTC. Offset-aware
values retain their specified offsets. Naive `start_time` and `end_time` fields
without an explicit UTC designation are not guessed and are skipped. A successful
import reconciles old operational records; an unsuccessful import preserves them.

Run `python ingest.py --year 2026 --source nascar` then `python audit.py`.


## v0.6
Grouped expandable weekends, month/week/upcoming views and Railway deployment files. See DEPLOY.md.