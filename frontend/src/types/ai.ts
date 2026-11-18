export type Severity = "critical" | "warning" | "info";
export type RiskLevel = "late" | "high" | "medium" | "low";

export interface ToolUsed { name: string; arguments: Record<string, unknown> }
export interface AskOut { answer: string; tools_used: ToolUsed[]; model: string; generated_at: string }
export interface ChatTurn { role: "user" | "assistant"; content: string }

export interface Anomaly {
  id: string; kind: string; severity: Severity; title: string; detail: string;
  vehicle_id: string; registration: string; transaction_id: string; occurred_at: string; evidence: Record<string, unknown>;
}
export interface Anomalies {
  days: number; items: Anomaly[]; counts: Record<string, number>; stats: Record<string, number>; methods: string[]; limitations: string[];
}
export interface DelayRisk {
  delivery_id: string; reference: string; status: string; deadline: string; minutes_left: number; estimated_trip_minutes: number | null;
  score: number; level: RiskLevel; reasons: string[]; vehicle: string | null; driver: string | null; dest_address: string;
}
export interface DelayRisks {
  items: DelayRisk[]; counts: Record<string, number>; open_deliveries: number; without_deadline: number; methods: string[]; assumptions: Record<string, number>;
}
export interface MaintenanceRisk {
  vehicle_id: string; registration: string; label: string; risk: "high" | "medium" | "low"; current_km: number;
  km_since_service: number | null; km_per_day: number | null; predicted_due_date: string | null; reasons: string[];
}
export interface MaintenanceForecast { items: MaintenanceRisk[]; counts: Record<string, number>; interval_km: number; methods: string[] }
export interface AISummary {
  ai_configured: boolean; fuel_anomalies: Record<string, number> | null; delay_risk: Record<string, number> | null; maintenance_risk: Record<string, number> | null;
}
export interface ReportSection { heading: string; bullets: string[] }
export interface Report {
  id: string | null; title: string; days: number; generated_at: string; sections: ReportSection[]; facts: Record<string, unknown>;
  narrative: string | null; narrative_note: string | null; model: string | null;
}
export interface ReportListItem { id: string; title: string; days: number; generated_at: string; has_narrative: boolean }
