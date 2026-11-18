export interface LivePosition {
  vehicle_id: string; registration: string; label: string; status: string; driver_label: string | null;
  lat: number; lng: number; speed_kph: number | null; heading: number | null; simulated: boolean;
}
export interface HistoryPoint { lat: number; lng: number; speed_kph: number | null; recorded_at: string; simulated: boolean }
export interface GeoEvent { event: "enter" | "exit"; vehicle_id: string | null; registration: string | null; geofence: string | null; at: string; simulated: boolean }
export interface Geofence { id: string; name: string; center_lat: number; center_lng: number; radius_m: number; is_active: boolean; created_at: string | null }

export interface StopIn { address: string; lat: number; lng: number; delivery_id?: string | null }
export interface Estimate { distance_km: number; duration_min: number; fuel_l: number }
export interface Assumptions {
  road_factor: number; avg_speed_kph: number; stop_minutes: number; fuel_l_per_100km: number;
  routing_provider?: string; profile?: string;
}
export interface PlanResult {
  order: number[]; stops: StopIn[]; original: Estimate; optimized: Estimate; saved: Estimate;
  saved_percent: number; assumptions: Assumptions; method: string;
}
export interface RouteStop { id: string; sequence: number; address: string; lat: number | null; lng: number | null; delivery_id: string | null }
export interface RouteRec {
  id: string; name: string; status: string; vehicle_id: string | null; vehicle_label: string | null;
  driver_id: string | null; driver_label: string | null; total_distance_km: number | null; est_duration_min: number | null;
  optimization_notes: (Record<string, unknown> & { assumptions?: Assumptions; saved_percent?: number; optimized?: Estimate | boolean }) | null;
  created_at: string | null; stop_count: number; stops: RouteStop[];
}
