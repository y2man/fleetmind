# FleetMind

AI-powered logistics and fleet management platform. **Status: Core fleet-management workflows are implemented; the planned production integrations are not complete.** See the evidence-based status and next steps in [docs/PROJECT_AUDIT.md](./docs/PROJECT_AUDIT.md).

## Run
Docker is optional for local development. The [Without Docker](#without-docker) section has Python and SQLite instructions for the backend and npm instructions for the frontend. Docker Compose runs the backend and frontend against the Supabase PostgreSQL database configured in `backend/.env`.

## Demo data, tests and deployment (Phase 9)
- **Demo data**: `SEED_DEMO_ON_START=true` (the default in `.env.example`) creates a fictional company with 14 vehicles, 12 drivers, about 190 deliveries, fuel and maintenance history, routes and geofences, including a few deliberate problems for the alerts and AI screening to find. Sign in as `owner@example.com`, `admin@example.com`, `dispatcher@example.com` or `viewer@example.com` (password `FleetMind-Demo-2026`), or press a role button on the sign-in page. Rebuild with `./scripts/seed-demo.sh --reset`. It never touches other organizations and refuses to run in production. Details: `docs/SEED.md`.
- **Production**: `docker-compose.prod.yml` (backend and nginx web tier using managed Supabase PostgreSQL), non-root backend image, health checks, required secrets, Resend/SMTP email, optional AfroMessage delivery SMS, private Supabase proof-of-delivery storage, backup script. HTTPS must be added in front. Steps and known limits: `docs/DEPLOYMENT.md`.
- **Tests and CI**: `cd backend && pytest` (the seed, its safety rules, roles, isolation and email are covered); `.github/workflows/ci.yml` runs the backend tests, the frontend build and the production image builds.
- Auth emails use Resend when `RESEND_API_KEY` and a verified `EMAIL_FROM` are configured; otherwise SMTP is used when configured.
- Users with delivery-write permission can manually send an SMS to the delivery's saved customer phone number; AfroMessage must be configured and the customer must have consented.

## Analytics and notifications (Phase 8)
- **Analytics** (`/app/analytics`): pick 7 days to 12 months or a custom range. KPIs show the change versus the previous period; charts for deliveries and for fuel and maintenance spend; fuel by vehicle, driver on-time table, delivery status. **Export CSV** (deliveries, fuel, maintenance, vehicles, drivers) and **PDF report** buttons download through the signed-in session.
- **Notification center**: the bell at the top and `/app/notifications`. Smart alerts (expiring documents, overdue maintenance, late deliveries, delay and maintenance risk, unusual fuel use) are raised once each; read state is per user.
- **Command palette** (Ctrl/⌘ + K or /) with global search over vehicles, drivers and deliveries, and **keyboard shortcuts** (`g` then `d`, `f`, `a`, ...; `?` shows all).
- No language model is used in this phase. Definitions, limits and endpoints: `docs/ANALYTICS.md`.
- Migration `0003_notifications_analytics` (a no-op on a fresh database).

## AI center (Phase 7)
- **Groq** (`openai/gpt-oss-120b`) powers the assistant and report summaries. Set `GROQ_API_KEY` in `.env` (backend only) and restart. Without a key the app still works; only the chat and the written report summary are off.
- **Ask** (`/app/ai`): plain-language questions answered from your own records through read-only tools. Each answer lists the data it used. Your question and the records needed are sent to Groq.
- **Fuel anomalies, delay risk, maintenance forecast**: statistics and rules computed in Python (no model), each with its method and limits shown. They are flags to review, not proof.
- **Reports**: computed figures plus an AI-written summary, saved per organization, copyable as text. The dashboard has an AI insights card.
- Details, endpoints and limits: `docs/AI.md`. No new migration.

## Tracking and routes (Phase 6)
- **Live map** (`/app/tracking`): Leaflet map with OpenStreetMap tiles (needs internet in the browser). Positions come from a **simulated GPS** feed over a WebSocket and are labeled demo everywhere. Only vehicles with status Active move. Simulation speed is boosted (`SIM_SPEED_BOOST`, default 8) so movement is visible.
- **Geofences**: circular zones (click the map to place one). Enter and exit events appear live, are stored in the audit log and create a notification row.
- **Routes** (`/app/routes`): single-route planner. Without `OSRM_BASE_URL`, distances are straight-line x a road factor. Configure OSRM to use road-network distances and durations; a provider outage returns an explicit service error. The `/app/fleet-planner` screen calls the OR-Tools preview API for multiple organization-owned vehicles with capacity limits, stop time windows, and driver shift bounds; preview results are not persisted.
- **GPS device management** (`/app/tracking`): issue and revoke tenant-scoped device tokens, ingest timestamped GPS points, and distinguish real device positions from simulated demo data.
- **Deliveries** now have pickup and destination latitude/longitude fields.
- WebSocket: `ws://localhost:8000/api/v1/ws/tracking`. Send `{"type":"auth","token":"<access token>"}` first (the token never goes in the URL). Updates arrive every `SIM_TICK_SECONDS` (default 2).
- Migration `0002_geofences` adds the geofences table (a no-op on a fresh database).
- Limits: the live hub is per backend process (multiple instances need Redis pub/sub); the simulation writes `last_lat/last_lng` on vehicles and history rows flagged `is_simulated`, kept for 1 hour. Redis can be enabled for shared rate limits and Celery-backed email; see [Deployment](./docs/DEPLOYMENT.md).

## Core modules (Phase 5)
Fleet, Drivers, Deliveries, Fuel and Maintenance have full create, read, update and delete, with search, filters, sorting and pagination (see docs/MODULES.md). The dashboard now shows real numbers from your organization's data; a new organization starts empty, while the demo organization (Phase 9) is pre-filled.
- **Proof of delivery**: upload, list, download, and delete PDF/JPEG/PNG/WebP evidence from a delivery's POD files page. Objects are stored in the configured private Supabase bucket and served only through tenant-authorized backend endpoints.

## Auth (Phase 4)
Sign up at /signup (you become the owner of a new organization). In development, if email delivery is unavailable, verification, reset and invitation links appear on screen ("Development mode" notice) and in the backend log. If Resend or SMTP successfully sends the email, the link is not returned by the API. Demo credentials are listed under Demo data (Phase 9).
The backend runs `alembic upgrade head` on start. Roles: owner, admin, dispatcher, viewer. Invite teammates from /app/team.

## Without Docker

The following commands are for PowerShell on Windows and use a local SQLite database. Run the backend and frontend in separate terminals.

**Backend terminal:**
```powershell
Set-Location .\backend
py -3.12 -m pip install -r requirements.txt
$env:DATABASE_URL = 'sqlite:///C:/Users/<your-user>/AppData/Local/Temp/fleetmind-local-dev.db'
$env:ENVIRONMENT = 'development'
$env:SECRET_KEY = 'dev-only-local-fleetmind-secret-key-change-me'
$env:CORS_ORIGINS = 'http://localhost:5173'
py -3.12 -m alembic upgrade head
py -3.12 -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
Replace `<your-user>` in the SQLite path with your Windows account name. Keep the backend terminal open. If port 8000 is already occupied, stop the existing backend process rather than launching a duplicate server.

**Frontend terminal:**
```powershell
Set-Location .\frontend
npm ci
npm run dev
```
Open http://localhost:5173; the frontend's default API URL is http://localhost:8000. The backend runs migrations on startup as well. Demo data is controlled by `SEED_DEMO_ON_START`; a Groq API key is optional and is needed only for model-backed AI responses.

For Docker-based development, copy `backend/.env.example` to `backend/.env`, set `DATABASE_URL` to the PostgreSQL URI from Supabase Dashboard → Connect → Postgres, then run `docker compose up --build`. There is no local PostgreSQL container. Switching databases does not migrate data from an existing local database.

## Verify
Phase 9: run the stack, open /signin, press **Owner**, then Sign in. The dashboard should show 14 vehicles; the bell should show Critical alerts (expired insurance, expired licence, overdue service) after a moment; AI > Fuel anomalies should flag ET-A1001 and ET-A1005. Run `./scripts/seed-demo.sh` again: it should say nothing changed.
Phase 8: sign up, add a vehicle with an insurance date in the past and a delivery with a past deadline that is not delivered. Open the bell: after a moment you should see a Critical and a Warning alert; click one to jump to its page. Open `/app/analytics`, switch the range, press **PDF report** and **Export CSV** > Deliveries (both should download). Press Ctrl+K, type part of a registration and press Enter; press `?` to see the shortcuts. Backend: `cd backend && pytest` (the new tests are `test_analytics_pure.py` and `test_phase8_api.py`).
Phase 3: the home page (/) is the landing page; /app/dashboard is the demo command center (change the date range, press Refresh); /app/design is the component showcase; /status shows the API and Groq model.

## Security
API keys live only in the backend `.env`. The health endpoint reports whether a key is set, never its value.

## Roadmap
1 Foundation · 2 Design system · 3 Landing + dashboard · 4 Auth + DB · 5 Core modules · 6 Tracking + routes · 7 AI center (Groq) · 8 Analytics + notifications · 9 Seed, tests, deploy
