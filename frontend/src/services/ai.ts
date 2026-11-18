import { api, del, post } from "./api";
import type { Health } from "@/types/health";
import type { AISummary, Anomalies, AskOut, ChatTurn, DelayRisks, MaintenanceForecast, Report, ReportListItem } from "@/types/ai";

export const aiApi = {
  health: () => api<Health>("/health"),
  summary: () => api<AISummary>("/ai/summary"),
  ask: (question: string, history: ChatTurn[]) => post<AskOut>("/ai/ask", { question, history }),
  anomalies: (days: number) => api<Anomalies>(`/ai/fuel-anomalies?days=${days}`),
  delayRisks: () => api<DelayRisks>("/ai/delay-risks"),
  maintenance: (intervalKm: number) => api<MaintenanceForecast>(`/ai/maintenance-forecast?interval_km=${intervalKm}`),
  reports: () => api<ReportListItem[]>("/ai/reports"),
  report: (id: string) => api<Report>(`/ai/reports/${id}`),
  createReport: (days: number) => post<Report>("/ai/reports", { days }),
  deleteReport: (id: string) => del(`/ai/reports/${id}`),
};
