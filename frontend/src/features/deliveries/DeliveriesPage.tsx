import { StatusBadge, fmtDateTime, titleCase } from "@/features/resource/format";
import { ResourcePage } from "@/features/resource/ResourcePage";
import type { ResourceConfig } from "@/features/resource/types";
import { Link } from "react-router-dom";
import type { Delivery } from "@/types/fleet";

const STATUS = ["pending", "assigned", "in_transit", "delivered", "delayed", "cancelled"].map((v) => ({ value: v, label: titleCase(v) }));

const cfg: ResourceConfig<Delivery> = {
  path: "deliveries", permission: "deliveries", title: "Deliveries", singular: "delivery",
  subtitle: "Orders from pickup to proof of delivery.", searchPlaceholder: "Search reference or address",
  defaultSort: "created_at", defaultOrder: "desc",
  columns: [
    { header: "Reference", sort: "reference", cell: (d) => <span className="font-medium">{d.reference}</span> },
    { header: "Route", cell: (d) => <span>{d.pickup_address}<span className="text-muted"> → </span>{d.dest_address}</span> },
    { header: "Status", sort: "status", cell: (d) => <StatusBadge value={d.status} /> },
    { header: "Proof", cell: (d) => <Link className="text-electric underline" to={`/app/deliveries/${d.id}/proof`}>POD files</Link> },
    { header: "Tracking", cell: (d) => <Link className="text-electric underline" to={`/app/deliveries/${d.id}/tracking`}>Share link</Link> },
    { header: "SMS", cell: (d) => d.customer_phone
      ? <Link className="text-electric underline" to={`/app/deliveries/${d.id}/sms`}>Message customer</Link>
      : <span className="text-muted">No phone</span> },
    { header: "Deadline", sort: "deadline", cell: (d) => fmtDateTime(d.deadline) },
    { header: "Vehicle", cell: (d) => d.vehicle_label ?? <span className="text-muted">–</span> },
    { header: "Driver", cell: (d) => d.driver_label ?? <span className="text-muted">–</span> },
  ],
  fields: [
    { name: "reference", label: "Reference", type: "text", required: true, optionalOnCreate: true, maxLength: 32, hint: "Leave empty to generate one." },
    { name: "status", label: "Status", type: "select", required: true, options: STATUS, hint: "Setting “Delivered” records the delivery time." },
    { name: "pickup_address", label: "Pickup address", type: "text", required: true, maxLength: 255 },
    { name: "dest_address", label: "Destination address", type: "text", required: true, maxLength: 255 },
    { name: "description", label: "Description", type: "textarea", maxLength: 2000 },
    { name: "pickup_lat", label: "Pickup latitude", type: "number", min: -90, max: 90, hint: "Optional. Used by route planning." },
    { name: "pickup_lng", label: "Pickup longitude", type: "number", min: -180, max: 180 },
    { name: "dest_lat", label: "Destination latitude", type: "number", min: -90, max: 90, hint: "Optional. Needed to add this delivery to a route." },
    { name: "dest_lng", label: "Destination longitude", type: "number", min: -180, max: 180 },
    { name: "weight_kg", label: "Weight (kg)", type: "number", min: 0, max: 1_000_000 },
    { name: "deadline", label: "Deadline", type: "datetime" },
    { name: "vehicle_id", label: "Vehicle", type: "vehicle" },
    { name: "driver_id", label: "Driver", type: "driver" },
  ],
  defaults: { status: "pending" },
  filters: [{ name: "status", label: "Statuses", options: STATUS }],
  describe: (d) => d.reference,
};

export const DeliveriesPage = () => <ResourcePage cfg={cfg} />;
