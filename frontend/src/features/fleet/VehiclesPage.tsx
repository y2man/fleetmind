import { ExpiryText, StatusBadge, fmtNum, titleCase } from "@/features/resource/format";
import { ResourcePage } from "@/features/resource/ResourcePage";
import type { ResourceConfig } from "@/features/resource/types";
import type { Vehicle } from "@/types/fleet";

const STATUS = ["active", "idle", "maintenance", "retired"].map((v) => ({ value: v, label: titleCase(v) }));
const FUEL = ["diesel", "petrol", "electric", "hybrid", "cng"].map((v) => ({ value: v, label: v === "cng" ? "CNG" : titleCase(v) }));

const cfg: ResourceConfig<Vehicle> = {
  path: "vehicles", permission: "vehicles", title: "Fleet", singular: "vehicle",
  subtitle: "Every vehicle in your organization.", searchPlaceholder: "Search registration, make or model",
  defaultSort: "created_at", defaultOrder: "desc",
  columns: [
    { header: "Registration", sort: "registration", cell: (v) => <span className="font-medium">{v.registration}</span> },
    { header: "Vehicle", sort: "manufacturer", cell: (v) => `${v.manufacturer} ${v.model}${v.year ? ` (${v.year})` : ""}` },
    { header: "Fuel", sort: "fuel_type", cell: (v) => (v.fuel_type === "cng" ? "CNG" : titleCase(v.fuel_type)) },
    { header: "Status", sort: "status", cell: (v) => <StatusBadge value={v.status} /> },
    { header: "Mileage", sort: "mileage_km", cell: (v) => `${fmtNum(v.mileage_km)} km` },
    { header: "Driver", cell: (v) => v.driver_label ?? <span className="text-muted">Unassigned</span> },
    { header: "Insurance", cell: (v) => <ExpiryText date={v.insurance_expiry} /> },
  ],
  fields: [
    { name: "registration", label: "Registration", type: "text", required: true, maxLength: 32 },
    { name: "manufacturer", label: "Manufacturer", type: "text", required: true, maxLength: 80 },
    { name: "model", label: "Model", type: "text", required: true, maxLength: 80 },
    { name: "year", label: "Year", type: "number", int: true, min: 1950, max: 2100 },
    { name: "fuel_type", label: "Fuel type", type: "select", required: true, options: FUEL },
    { name: "status", label: "Status", type: "select", required: true, options: STATUS },
    { name: "mileage_km", label: "Mileage (km)", type: "number", required: true, int: true, min: 0, max: 10_000_000 },
    { name: "capacity_kg", label: "Capacity (kg)", type: "number", int: true, min: 0, max: 1_000_000 },
    { name: "driver_id", label: "Assigned driver", type: "driver" },
    { name: "insurance_expiry", label: "Insurance expiry", type: "date" },
    { name: "registration_expiry", label: "Registration expiry", type: "date" },
  ],
  defaults: { fuel_type: "diesel", status: "idle", mileage_km: "0" },
  filters: [{ name: "status", label: "Statuses", options: STATUS }, { name: "fuel_type", label: "Fuel types", options: FUEL }],
  describe: (v) => v.registration,
  deleteNote: "Its fuel and maintenance records are deleted too; deliveries keep existing but lose the vehicle.",
};

export const VehiclesPage = () => <ResourcePage cfg={cfg} />;
