export interface AnalyticsKpi {
  key: string; label: string; value: number | null; previous: number | null; suffix: string; decimals: number;
  good: "up" | "down" | "neutral"; change_pct: number | null;
}
export interface AnalyticsPoint {
  label: string; start: string; created: number; delivered: number; late: number; fuel_cost: number; liters: number; maintenance_cost: number;
}
export interface Analytics {
  range: { start: string; end: string; days: number; bucket_days: number };
  previous_range: { start: string; end: string };
  kpis: AnalyticsKpi[];
  series: AnalyticsPoint[];
  delivery_status: { status: string; count: number }[];
  fuel_by_vehicle: { vehicle: string; liters: number; cost: number; fills: number; cost_per_liter: number | null }[];
  drivers: { driver: string; delivered: number; judged: number; on_time: number; late: number; on_time_rate_pct: number | null }[];
  maintenance_by_kind: { kind: string; count: number; cost: number }[];
  vehicles_by_status: Record<string, number>;
  notes: string[];
  has_data: boolean;
}
export type RangeParams = { days: number } | { start: string; end: string };

export interface AppNotification {
  id: string; severity: "info" | "warning" | "critical"; title: string; body: string | null; kind: string | null; link: string | null;
  created_at: string; is_read: boolean;
}
export interface NotificationList { items: AppNotification[]; unread_count: number }
export interface RefreshResult { created: number; unread_count: number }

export interface SearchHit { type: "vehicle" | "driver" | "delivery"; id: string; title: string; subtitle: string | null; url: string }
export interface SearchResult { query: string; results: SearchHit[] }
