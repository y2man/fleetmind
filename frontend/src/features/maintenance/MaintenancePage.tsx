import { Badge } from "@/components/ui";
import { StatusBadge, daysUntil, fmtDate, fmtNum, titleCase } from "@/features/resource/format";
import { ResourcePage } from "@/features/resource/ResourcePage";
import type { ResourceConfig } from "@/features/resource/types";
import type { Maintenance } from "@/types/fleet";

const STATUS = ["scheduled", "in_progress", "completed", "cancelled"].map((v) => ({ value: v, label: titleCase(v) }));
const KIND = ["preventive", "repair", "inspection"].map((v) => ({ value: v, label: titleCase(v) }));

const cfg: ResourceConfig<Maintenance> = {
  path: "maintenance", permission: "maintenance", title: "Maintenance", singular: "maintenance task",
  subtitle: "Scheduled and completed service work.", searchPlaceholder: "Search description",
  defaultSort: "scheduled_for", defaultOrder: "asc",
  columns: [
    { header: "Scheduled", sort: "scheduled_for", cell: (m) => (
      <span className="inline-flex flex-wrap items-center gap-2">{fmtDate(m.scheduled_for)}{m.status === "scheduled" && m.scheduled_for && daysUntil(m.scheduled_for) < 0 ? <Badge tone="danger">Overdue</Badge> : null}</span>
    ) },
    { header: "Vehicle", cell: (m) => m.vehicle_label ?? "–" },
    { header: "Type", sort: "kind", cell: (m) => <StatusBadge value={m.kind} /> },
    { header: "Description", cell: (m) => m.description },
    { header: "Status", sort: "status", cell: (m) => <StatusBadge value={m.status} /> },
    { header: "Cost", sort: "cost", cell: (m) => fmtNum(m.cost, 2) },
  ],
  fields: [
    { name: "vehicle_id", label: "Vehicle", type: "vehicle", required: true },
    { name: "kind", label: "Type", type: "select", required: true, options: KIND },
    { name: "description", label: "Description", type: "text", required: true, maxLength: 255, full: true },
    { name: "status", label: "Status", type: "select", required: true, options: STATUS, hint: "Completing a task records the completion time." },
    { name: "scheduled_for", label: "Scheduled for", type: "date" },
    { name: "cost", label: "Cost", type: "number", min: 0, max: 10_000_000 },
    { name: "odometer_km", label: "Odometer (km)", type: "number", int: true, min: 0, max: 10_000_000 },
  ],
  defaults: { kind: "preventive", status: "scheduled" },
  filters: [{ name: "status", label: "Statuses", options: STATUS }, { name: "kind", label: "Types", options: KIND }],
  describe: (m) => `${m.description}${m.vehicle_label ? ` (${m.vehicle_label.split(" · ")[0]})` : ""}`,
};

export const MaintenancePage = () => <ResourcePage cfg={cfg} />;
