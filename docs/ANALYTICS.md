# Analytics, exports, notifications and search (Phase 8)

## Endpoints (all under `/api/v1`, all need a signed-in user, all limited to the caller's organization)

| Endpoint | Permission | What it does |
|---|---|---|
| `GET /analytics?days=30` or `?start=YYYY-MM-DD&end=YYYY-MM-DD` | `analytics:read` | KPIs with change versus the previous period, chart series, status split, fuel by vehicle, driver on-time table, maintenance by kind |
| `GET /analytics/export/{dataset}` (same range params) | `analytics:read` + `{dataset}:read` | CSV of `vehicles`, `drivers`, `deliveries`, `fuel` or `maintenance` |
| `GET /analytics/report` (same range params) | `analytics:read` | PDF report of the same figures |
| `GET /notifications?unread_only=&limit=` | `analytics:read` | The caller's notifications and unread count |
| `POST /notifications/refresh` | `analytics:read` | Run the smart-alert rules and save new alerts |
| `POST /notifications/{id}/read`, `POST /notifications/read-all` | `analytics:read` | Mark read (per user) |
| `GET /search?q=` | `analytics:read` | Vehicles, drivers and deliveries matching the text (only kinds the caller can read; 5 per kind) |

Range rules: `days` is 1 to 366 (default 30), or give both `start` and `end` (at most 366 days, end not in the future). Anything else returns 422.

## How the numbers are defined
- Days are **UTC calendar days**, both ends included. FleetMind does not store a per-organization time zone yet, so activity near midnight can land on the neighbouring local day.
- The **previous period** is the same number of days directly before the range. A percent change is blank when the previous value is zero or missing.
- A delivery is **late** when its deadline falls in the range and it is marked delayed, is still open past its deadline, or was delivered after its deadline.
- **On-time rate** only counts completed deliveries that had a deadline; the notes under the charts say how many were left out.
- Charts group days per point: 1 (up to 31 days), 7 (up to 180 days), 30 (longer).
- Fuel and maintenance amounts have **no currency** in FleetMind; they are shown as entered.
- No language model is involved anywhere in Phase 8. Everything is arithmetic and rules over your own records.

## Smart alerts
`POST /notifications/refresh` (the app calls it when it opens and every 5 minutes) checks:
expired or soon-to-expire documents (30 days), overdue maintenance, late deliveries, high delivery delay risk, high maintenance risk and unusual fuel purchases (last 30 days). The last three reuse the Phase 7 screening, so they carry the same limits (flags to review, not proof).

- Each condition has a stable `dedupe_key` (for example the document and its expiry date), so it is raised **once** per organization, even after it is read. When the fact changes (a renewed document, a new anomaly) the key changes and a new alert appears.
- At most 50 new alerts are created per refresh, so a first run on a large fleet is spread over a few refreshes instead of flooding the bell.
- Read state is **per user** (`notification_reads`). A notification with no `user_id` is visible to the whole organization; geofence notifications from Phase 6 are of this kind.
- Notifications are kept; there is no automatic cleanup yet.

## Exports
- CSV opens in Excel (UTF-8 with a byte-order mark). Text cells that start with `=`, `+`, `-`, `@`, tab or carriage return get a leading apostrophe so a spreadsheet cannot run them as a formula.
- `deliveries`, `fuel` and `maintenance` follow the date range (deliveries by created date, fuel by purchase date, maintenance by scheduled date, or created date if none). `vehicles` and `drivers` are always the full list.
- Limit: 50,000 rows per file (422 beyond that), 20 exports per minute per IP (in memory).
- Every export is written to the audit log (`export.csv`, `export.pdf`) with the dataset, row count and range.
- The PDF is produced by a small built-in writer (`services/pdf.py`), so no extra package or system library is needed. It prints Windows-1252 characters; others appear as `?`.

## Command palette, search and shortcuts (frontend)
- **Ctrl/⌘ + K** or **/** opens the palette: pages you may open, a few commands, and live record search (2+ characters). A record result opens its list page with the search box filled in.
- **g** then a key jumps to a page (`d` dashboard, `f` fleet, `r` drivers, `e` deliveries, `l` live map, `o` routes, `u` fuel, `m` maintenance, `a` analytics, `i` AI center, `n` notifications). **?** shows the list.
- Shortcuts do nothing while you type in a field or while a dialog is open. The list lives in `frontend/src/config/shortcuts.ts`, and the help dialog reads from it.

## Migration
`0003_notifications_analytics` adds `notifications.kind`, `link`, `dedupe_key` (unique per organization), an index, and the `notification_reads` table. On a brand-new database these already exist from the baseline and the migration does nothing.

## Known limits
- Rate limits are per IP and in memory (one API instance). Move them to Redis before running several instances.
- Alerts are checked by the app while someone has it open. There is no background scheduler yet, so nothing is raised while nobody is signed in.
- Email and push delivery of alerts is not built; alerts live in the app.
