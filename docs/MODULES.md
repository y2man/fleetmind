# Core modules (Phase 5)

All endpoints live under `/api/v1` and need a bearer token.

| Collection | Permission (read / write) | Filters | Sortable columns |
|---|---|---|---|
| `/vehicles` | `vehicles:read` / `vehicles:write` | status, fuel_type, driver_id | registration, manufacturer, model, year, status, fuel_type, mileage_km, created_at |
| `/drivers` | `drivers:read` / `drivers:write` | availability | full_name, license_number, license_expiry, availability, safety_score, created_at |
| `/deliveries` | `deliveries:read` / `deliveries:write` | status, vehicle_id, driver_id | reference, status, deadline, weight_kg, delivered_at, created_at |
| `/fuel` | `fuel:read` / `fuel:write` | vehicle_id, driver_id | occurred_at, liters, cost, odometer_km |
| `/maintenance` | `maintenance:read` / `maintenance:write` | status, kind, vehicle_id | scheduled_for, status, kind, cost, created_at |

Each collection supports `GET /`, `POST /`, `GET /{id}`, `PATCH /{id}` and `DELETE /{id}`. `/vehicles` and `/drivers` also have `GET /options` (id + label, used by the form dropdowns).

List parameters: `page`, `page_size` (1-100), `q` (case-insensitive search over the text columns), `sort`, `order` (`asc`/`desc`) plus the filters above. Responses look like `{items, total, page, page_size}`. An unknown `sort` value is ignored.

`GET /dashboard?days=7|30|90` returns KPIs, chart series, alerts, recent activity and upcoming maintenance, all computed from the caller's organization.

## Rules enforced on the server
- Every query is scoped to the caller's organization. Another organization's ids return 404.
- `vehicle_id` / `driver_id` must belong to the same organization (otherwise 422).
- Unique per organization: vehicle registration, driver license number, delivery reference (409 on conflict).
- Setting a delivery to `delivered` or a maintenance task to `completed` records the time. Moving a delivery out of `delivered` clears it.
- Deleting a driver unassigns their vehicles and deliveries. Deleting a vehicle also deletes its fuel and maintenance records.
- Create, update and delete are written to the audit log (`vehicle.created`, `delivery.updated`, ...).
- Roles: owner and admin write everything; dispatcher writes deliveries and routes; viewer is read-only.

## Dashboard definitions
- Delayed: status `delayed`, or still open (pending/assigned/in transit) with a deadline in the past.
- Delivery success: completed / (completed + delayed) in the selected range. Shown as "–" when there is nothing to compare.
- Fleet utilization: active vehicles / vehicles not retired.
- Alerts: insurance, registration and license dates expired or within 30 days; overdue scheduled maintenance; late deliveries.

## Not in this phase
Coordinates for deliveries (Phase 6 map and routing), AI insights (Phase 7), CSV/PDF export (Phase 8), seed data (done in Phase 9, see SEED.md). No database migration was needed: the Phase 4 migration already created these tables.

## Phase 6 endpoints
- `GET/POST /geofences`, `GET/PATCH/DELETE /geofences/{id}` (permission routes:read / routes:write)
- `POST /routes/plan` (preview, nothing saved), `GET/POST /routes`, `GET/PATCH/DELETE /routes/{id}`
- `GET /tracking/vehicles` (last positions), `GET /tracking/vehicles/{id}/history`, `GET /tracking/events`
- `WS /ws/tracking` (first message authenticates; messages: `snapshot`, `positions`, `geofence`)
