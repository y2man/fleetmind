# AI center (Phase 7)

Provider: **Groq**, model `openai/gpt-oss-120b` (`GROQ_MODEL`). The API key lives only in the backend `.env`
(`GROQ_API_KEY`) and is never returned by any endpoint or sent to the browser.

## What is AI and what is not
| Feature | How it works |
|---|---|
| Ask (chat) | The model calls fixed, read-only data tools. It never writes SQL and cannot change data. |
| Fuel anomalies | **Statistics, no model.** Robust z-scores on consumption, fill size and price, plus data-quality checks. |
| Delay risk | **Rules, no model.** A 0-99 score from time left, estimated trip time, assignment and driver/vehicle state. |
| Maintenance forecast | **Rules, no model.** Overdue jobs, km since last preventive service, repair frequency. |
| Executive report | Figures are computed in Python. If AI is configured, the model writes a short summary from those figures only. |

Because the screening is deterministic, it works without a Groq key and gives the same answer every time.
Results are flags to review, not proof, and every panel shows its method and limits.

## Endpoints (`/api/v1`, permission `ai:use`: owner, admin, dispatcher)
- `POST /ai/ask` `{question, history[]}`: history may only contain `user`/`assistant` text (max 12 messages). Returns the answer and which data tools were used. 20 requests/min per IP.
- `GET /ai/fuel-anomalies?days=7..365`, `GET /ai/delay-risks`, `GET /ai/maintenance-forecast?interval_km=1000..100000`
- `GET /ai/summary`: counts for the dashboard card (no model call).
- `POST /ai/reports` `{days: 7|30|90}`, `GET /ai/reports`, `GET /ai/reports/{id}`, `DELETE /ai/reports/{id}`: reports are saved in `ai_insights` (kind `executive_report`). No migration is needed.

Each endpoint also needs the read permission of the data it uses (for example `fuel:read`).

## Assistant tools
`fleet_overview`, `search_vehicles`, `search_drivers`, `search_deliveries`, `fuel_summary`, `maintenance_overview`,
`expiring_documents`, `driver_performance`, `fuel_anomalies`, `delivery_delay_risks`, `maintenance_forecast`.
A tool is offered only if the user's role can read its data. Every tool is limited to the user's organization.
Results leave out emails, phone numbers and licence numbers and are capped in size. At most `AI_MAX_TOOL_ROUNDS` (5) tool rounds per question.

## Safety and privacy
- Record text (descriptions, addresses, station names) and tool output are treated as untrusted data in the system prompt.
- The audit log records `ai.ask` with the tool names and question length, not the question or answer text.
- **Your question and the records the tools return are sent to Groq.** Keep this in mind for sensitive data.
- Errors from Groq (bad key, rate limit, timeout) are turned into short messages; the key is never logged or shown.

## Settings (backend `.env`)
`GROQ_API_KEY`, `GROQ_MODEL`, `GROQ_REASONING_EFFORT` (low/medium/high), `AI_TIMEOUT_SECONDS` (60), `AI_MAX_TOOL_ROUNDS` (5).

## Known limits
- Fuel cost has no currency. Prices are only compared with each other.
- Consumption screening assumes the tank is filled each time and needs odometer readings (at least 6 purchases per vehicle).
- Delay risk uses straight-line trip estimates (road factor 1.3, 40 km/h, 10 min per stop), not road routing, and ignores live GPS (it is simulated).
- Maintenance mileage checks need a completed preventive record with an odometer; the 10,000 km interval is an assumption you can change in the panel.
- Analytics load the organization's records into memory (same approach as the dashboard). Very large fleets should move this to SQL aggregation in Phase 8.
- Rate limiting is per IP and in memory.
