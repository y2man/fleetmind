/** Demo accounts created by `python -m app.seed` (backend/app/seed/generator.py). Keep both in sync; a backend test checks it. */
export const DEMO_PASSWORD = "FleetMind-Demo-2026";
export const DEMO_ACCOUNTS = [
  { role: "Owner", email: "owner@example.com" },
  { role: "Admin", email: "admin@example.com" },
  { role: "Dispatcher", email: "dispatcher@example.com" },
  { role: "Viewer", email: "viewer@example.com" },
] as const;
