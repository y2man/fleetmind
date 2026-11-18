import { api, download, post } from "./api";
import type { Analytics, NotificationList, RangeParams, RefreshResult, SearchResult } from "@/types/analytics";

const rangeQuery = (r: RangeParams) => ("days" in r ? `days=${r.days}` : `start=${r.start}&end=${r.end}`);

export const analyticsApi = {
  get: (r: RangeParams) => api<Analytics>(`/analytics?${rangeQuery(r)}`),
  csv: (dataset: string, r: RangeParams) => download(`/analytics/export/${dataset}?${rangeQuery(r)}`, `fleetmind-${dataset}.csv`),
  pdf: (r: RangeParams) => download(`/analytics/report?${rangeQuery(r)}`, "fleetmind-report.pdf"),
};

export const notificationsApi = {
  list: (opts: { unreadOnly?: boolean; limit?: number } = {}) => api<NotificationList>(`/notifications?limit=${opts.limit ?? 30}${opts.unreadOnly ? "&unread_only=true" : ""}`),
  refresh: () => post<RefreshResult>("/notifications/refresh"),
  read: (id: string) => post<RefreshResult>(`/notifications/${id}/read`),
  readAll: () => post<RefreshResult>("/notifications/read-all"),
};

export const searchApi = { query: (q: string) => api<SearchResult>(`/search?q=${encodeURIComponent(q)}`) };
