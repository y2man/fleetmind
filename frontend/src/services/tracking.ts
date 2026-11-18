import { api, del, patch, post } from "./api";
import { resource, type Params } from "./resources";
import type { Page } from "@/types/fleet";
import type { Assumptions, GeoEvent, Geofence, HistoryPoint, LivePosition, PlanResult, RouteRec, StopIn } from "@/types/tracking";

export const trackingApi = {
  positions: () => api<LivePosition[]>("/tracking/vehicles"),
  history: (id: string, limit = 60) => api<HistoryPoint[]>(`/tracking/vehicles/${id}/history?limit=${limit}`),
  events: () => api<GeoEvent[]>("/tracking/events"),
};

export const geofenceApi = resource<Geofence>("geofences");

export const routesApi = {
  list: (p: Params = {}) => api<Page<RouteRec>>(`/routes?page_size=${p.page_size ?? 20}`),
  get: (id: string) => api<RouteRec>(`/routes/${id}`),
  plan: (stops: StopIn[], assumptions: Assumptions) => post<PlanResult>("/routes/plan", { stops, assumptions }),
  create: (body: { name: string; stops: StopIn[]; assumptions: Assumptions; optimize: boolean; vehicle_id?: string; driver_id?: string }) => post<RouteRec>("/routes", body),
  setStatus: (id: string, status: string) => patch<RouteRec>(`/routes/${id}`, { status }),
  remove: (id: string) => del(`/routes/${id}`),
};
