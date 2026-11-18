import { ExpiryText, StatusBadge, fmtNum, titleCase } from "@/features/resource/format";
import { ResourcePage } from "@/features/resource/ResourcePage";
import type { ResourceConfig } from "@/features/resource/types";
import type { Driver } from "@/types/fleet";

const AVAIL = ["available", "on_duty", "off_duty", "on_leave"].map((v) => ({ value: v, label: titleCase(v) }));

const cfg: ResourceConfig<Driver> = {
  path: "drivers", permission: "drivers", title: "Drivers", singular: "driver",
  subtitle: "Your drivers, licenses and availability.", searchPlaceholder: "Search name, license or email",
  defaultSort: "created_at", defaultOrder: "desc",
  columns: [
    { header: "Name", sort: "full_name", cell: (d) => <span className="font-medium">{d.full_name}</span> },
    { header: "Contact", cell: (d) => (d.email || d.phone ? <>{d.email}{d.email && d.phone ? <br /> : null}{d.phone}</> : <span className="text-muted">–</span>) },
    { header: "License", sort: "license_number", cell: (d) => d.license_number },
    { header: "License expiry", sort: "license_expiry", cell: (d) => <ExpiryText date={d.license_expiry} /> },
    { header: "Availability", sort: "availability", cell: (d) => <StatusBadge value={d.availability} /> },
    { header: "Safety score", sort: "safety_score", cell: (d) => fmtNum(d.safety_score, 1) },
  ],
  fields: [
    { name: "full_name", label: "Full name", type: "text", required: true, maxLength: 160 },
    { name: "license_number", label: "License number", type: "text", required: true, maxLength: 64 },
    { name: "email", label: "Email", type: "email", maxLength: 254 },
    { name: "phone", label: "Phone", type: "text", maxLength: 40 },
    { name: "license_expiry", label: "License expiry", type: "date" },
    { name: "availability", label: "Availability", type: "select", required: true, options: AVAIL },
    { name: "safety_score", label: "Safety score (0–100)", type: "number", min: 0, max: 100 },
  ],
  defaults: { availability: "available" },
  filters: [{ name: "availability", label: "Availability", options: AVAIL }],
  describe: (d) => d.full_name,
  deleteNote: "Vehicles and deliveries assigned to this driver become unassigned.",
};

export const DriversPage = () => <ResourcePage cfg={cfg} />;
