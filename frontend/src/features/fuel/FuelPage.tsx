import { fmtDateTime, fmtNum } from "@/features/resource/format";
import { ResourcePage } from "@/features/resource/ResourcePage";
import type { ResourceConfig } from "@/features/resource/types";
import type { Fuel } from "@/types/fleet";

const cfg: ResourceConfig<Fuel> = {
  path: "fuel", permission: "fuel", title: "Fuel", singular: "fuel entry",
  subtitle: "Fuel purchases per vehicle. Amounts are shown as entered (no currency conversion).", searchPlaceholder: "Search station",
  defaultSort: "occurred_at", defaultOrder: "desc",
  columns: [
    { header: "Date", sort: "occurred_at", cell: (f) => fmtDateTime(f.occurred_at) },
    { header: "Vehicle", cell: (f) => f.vehicle_label ?? "–" },
    { header: "Liters", sort: "liters", cell: (f) => fmtNum(f.liters, 1) },
    { header: "Cost", sort: "cost", cell: (f) => fmtNum(f.cost, 2) },
    { header: "Cost / L", cell: (f) => (f.liters > 0 ? fmtNum(f.cost / f.liters, 2) : "–") },
    { header: "Odometer", sort: "odometer_km", cell: (f) => (f.odometer_km === null ? "–" : `${fmtNum(f.odometer_km)} km`) },
    { header: "Station", cell: (f) => f.station ?? <span className="text-muted">–</span> },
    { header: "Driver", cell: (f) => f.driver_label ?? <span className="text-muted">–</span> },
  ],
  fields: [
    { name: "vehicle_id", label: "Vehicle", type: "vehicle", required: true },
    { name: "driver_id", label: "Driver", type: "driver" },
    { name: "liters", label: "Liters", type: "number", required: true, min: 0.01, max: 10_000 },
    { name: "cost", label: "Total cost", type: "number", required: true, min: 0, max: 10_000_000 },
    { name: "odometer_km", label: "Odometer (km)", type: "number", int: true, min: 0, max: 10_000_000 },
    { name: "station", label: "Station", type: "text", maxLength: 120 },
    { name: "occurred_at", label: "Date and time", type: "datetime", hint: "Leave empty to use the current time." },
  ],
  filters: [],
  describe: (f) => `${fmtNum(f.liters, 1)} L for ${f.vehicle_label ?? "a vehicle"}`,
};

export const FuelPage = () => <ResourcePage cfg={cfg} />;
