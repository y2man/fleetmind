export interface Page<T> { items: T[]; total: number; page: number; page_size: number }
export interface IdOption { id: string; label: string }

interface Base { id: string; created_at: string | null; is_demo: boolean }
export interface Vehicle extends Base {
  registration: string; manufacturer: string; model: string; year: number | null; fuel_type: string; status: string;
  mileage_km: number; capacity_kg: number | null; driver_id: string | null; driver_label: string | null;
  insurance_expiry: string | null; registration_expiry: string | null;
}
export interface Driver extends Base {
  full_name: string; email: string | null; phone: string | null; license_number: string; license_expiry: string | null;
  availability: string; safety_score: number | null;
}
export interface Delivery extends Base {
  reference: string; status: string; description: string | null; weight_kg: number | null;
  pickup_address: string; dest_address: string; pickup_lat: number | null; pickup_lng: number | null; dest_lat: number | null; dest_lng: number | null; deadline: string | null; delivered_at: string | null;
  customer_name: string | null; customer_phone: string | null; customer_email: string | null;
  vehicle_id: string | null; vehicle_label: string | null; driver_id: string | null; driver_label: string | null;
}
export interface DeliveryDocument {
  id: string; delivery_id: string; filename: string; content_type: string; size_bytes: number; created_at: string;
}
export interface Fuel extends Base {
  vehicle_id: string; vehicle_label: string | null; driver_id: string | null; driver_label: string | null;
  liters: number; cost: number; odometer_km: number | null; station: string | null; occurred_at: string;
}
export interface Maintenance extends Base {
  vehicle_id: string; vehicle_label: string | null; kind: string; description: string; status: string;
  cost: number | null; odometer_km: number | null; scheduled_for: string | null; completed_at: string | null;
}

export interface Kpi { key: string; label: string; value: number | null; suffix: string; decimals: number }
export interface SeriesPoint { label: string; completed: number; delayed: number; cost: number }
export interface Dashboard {
  days: number; kpis: Kpi[]; deliveries: SeriesPoint[]; fuel: SeriesPoint[];
  vehicle_status: Record<string, number>;
  alerts: { severity: "critical" | "warning"; text: string }[];
  activity: { text: string; at: string }[];
  maintenance: { vehicle: string; task: string; due: string | null; overdue: boolean }[];
  has_data: boolean;
}
