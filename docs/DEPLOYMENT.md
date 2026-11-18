# Deployment (Phase 9)

Target: one Linux server (a small VM is enough) with Docker and Docker Compose, using `docker-compose.prod.yml`. The stack runs **backend** (FastAPI, runs migrations on start) and **web** (nginx: serves the built site and proxies `/api`, including the live-tracking WebSocket, to the backend). PostgreSQL is hosted by Supabase; Compose does not start or store a local database. Only `web` is published. Redis and the Celery worker are opt-in under the `async` Compose profile.

## 1. Configure
```
cp .env.production.example .env
./scripts/gen-secrets.sh        # paste SECRET_KEY into .env
```
Set `DATABASE_URL` to the PostgreSQL connection URI from Supabase Dashboard → **Connect** → **Postgres**. Replace the password placeholder locally, URL-encode special characters in the password, and keep the URI private. `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` are separate settings for Storage; they are not database credentials. Moving the connection does not copy records from a previous local database; migrate existing data separately before switching production traffic. Set `PUBLIC_URL` to the exact address users will type (for example `https://fleet.example.com`). The backend refuses to start in production with a placeholder `SECRET_KEY`. Add `GROQ_API_KEY` for AI features. For email, configure either `RESEND_API_KEY` plus a verified `EMAIL_FROM`, or SMTP settings (below). Resend is preferred when both providers are configured.

## 2. Start
```
docker compose -f docker-compose.prod.yml --env-file .env up -d --build
docker compose -f docker-compose.prod.yml ps        # backend and web should become "healthy"
curl http://localhost/api/v1/health
```
The backend applies `alembic upgrade head` on every start. Then open the site and sign up: the first account creates its organization and is its owner. Demo data is never created in production.

## 3. HTTPS (required)
In production the refresh cookie is marked `Secure`, so sign-in only works over HTTPS. Terminate TLS in front of the `web` container. Simplest with Caddy on the same host (automatic certificates), with `HTTP_PORT=8080` in `.env`:
```
fleet.example.com {
    reverse_proxy localhost:8080
}
```
A cloud load balancer or Cloudflare works too. WebSocket upgrades must be allowed (Caddy does this by default). The backend trusts `X-Forwarded-For` so rate limits and the audit log see real client addresses; that is only safe because the backend port is not published. Do not add a `ports:` entry to `backend`.

## 4. Email
For Resend, set `RESEND_API_KEY` and `EMAIL_FROM` to a sender/domain verified in your Resend account. If the Resend key is absent, FleetMind uses SMTP when `SMTP_HOST` is set: configure `SMTP_PORT` (587 STARTTLS or 465 TLS), `SMTP_USER`, `SMTP_PASSWORD` and `SMTP_FROM`. If neither provider is configured, messages are logged for development. Provider failures are logged without logging one-time link contents and do not break sign-up. Verification email is sent but sign-in does not currently require a verified address.

Email delivery is synchronous by default. To queue messages, set `EMAIL_DELIVERY_BACKEND=celery` and start the profile services with `docker compose -f docker-compose.prod.yml --env-file .env --profile async up -d --build`. The worker and API must use the same reachable `REDIS_URL`. On local Windows development, run the worker from `backend` with `py -3.12 -m celery -A app.celery_app:celery_app worker --pool=solo --loglevel=INFO`.

Redis-backed shared rate limiting is also opt-in: set `RATE_LIMIT_BACKEND=redis` and enable the `async` profile (or configure a reachable Redis service yourself). Redis errors return `503`; limits do not silently fall back to per-process memory. The default `memory` mode preserves single-process behavior.

## 5. Private proof-of-delivery storage
Create a **private** bucket named by `SUPABASE_BUCKET` (default `fleetmind-documents`) in Supabase Storage, then set `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` in the backend environment. Keep the service-role key server-side; never expose it as a `VITE_*` setting. Delivery proof files are uploaded through the authenticated API and served through tenant-checked API routes, not public object URLs. The backend accepts PDF, JPEG, PNG, and WebP files up to `DOCUMENT_MAX_BYTES` (default 10 MB). Apply your organization's retention policy before using this for regulated records.

## 6. GPS devices and customer links
Create a GPS credential through `POST /api/v1/integrations/gps/credentials` while authenticated with vehicle-write permission. The plaintext `token` is returned once; store it securely on the device. Send timestamped JSON positions to `POST /api/v1/integrations/gps/positions` with `X-GPS-Token: <token>` and `recorded_at` in ISO-8601 with a timezone. Revoke a device credential through `DELETE /api/v1/integrations/gps/credentials/{id}`. Vendor-specific payloads need an adapter that maps them to this contract.

Customer tracking links can be created, listed, and revoked on the delivery tracking page. The create response contains the shareable secret URL once; list responses never contain its token.

## 7. Delivery SMS
Set `AFROMESSAGE_API_KEY`, `AFROMESSAGE_IDENTIFIER_ID`, and (if approved for your account) `AFROMESSAGE_SENDER` in the backend environment. The identifier ID is the AfroMessage identifier used as the send API's `from` value; it is different from the sender label. Keep the API key server-side. Users with delivery-write permission can open a delivery's SMS action and send a message only to its saved customer phone number. The phone must use E.164 format, and the user must confirm the customer consented before sending. Each request is rate-limited; the API reports provider acceptance/message ID, not confirmed handset delivery. No SMS is sent automatically.

## 8. Operate
| Task | Command |
|---|---|
| Logs | `docker compose -f docker-compose.prod.yml logs -f backend` |
| Update | `git pull && docker compose -f docker-compose.prod.yml --env-file .env up -d --build` |
| Back up | `./scripts/backup-db.sh` (uses `pg_dump` in a temporary Postgres client container and writes `backups/*.sql.gz`; copy files off-server and test a restore) |
| Restore | `gunzip -c backups/FILE.sql.gz \| docker run --rm -i --env-file .env postgres:16-alpine sh -c 'psql "$DATABASE_URL"'` into the intended database |
| Stop | `docker compose -f docker-compose.prod.yml down` (Supabase data is managed separately) |

## Known limits (be aware before going live)
- **One backend process for live tracking.** The live-tracking hub and alert dedupe remain per process; Redis only shares HTTP rate limits and Celery email tasks.
- **Database backups.** Supabase-managed backups depend on your Supabase plan. The included script makes a logical dump using the configured connection URI; store dumps securely because they contain organization data.
- **GPS device integration.** The live-map screen can issue and revoke device credentials, but each GPS vendor still needs a small adapter to post authenticated, timestamped coordinates to the ingestion API; the demo simulator remains separately labeled.
- **Routing.** Without `OSRM_BASE_URL`, route estimates use straight-line distance times a road factor. With OSRM configured, route planning uses its road distance/duration matrix and fails with `503` if the provider is unavailable. The `/app/fleet-planner` screen calls the OR-Tools preview API across organization-owned, capacity-configured vehicles; it accepts start coordinates, driver shift bounds, stop demand, time windows, and service times. It does not persist routes. Existing route creation remains a single-route nearest-neighbour + 2-opt workflow.
- **AfroMessage credentials and delivery are not live-verified.** Sending uses the documented API contract, but you must configure an approved identifier, verify the sender/account, and test with consented numbers before production use. The balance diagnostic alone does not verify message delivery.
- **No automatic backups, monitoring or log shipping** are included; use your host's or add them.
- **No Content-Security-Policy header** is set (the map loads tiles from OpenStreetMap); add one once you have tested it against your setup.
- Install frontend dependencies with `npm ci` to honor the committed `frontend/package-lock.json` and keep builds reproducible.
- **Not load-tested.** Sizing is untested; start small and watch memory.

## Continuous integration
`.github/workflows/ci.yml` runs the backend tests, builds the frontend (type-check + bundle), checks that the production compose file demands its secrets, and builds both production images.
