import { api, del, patch, post } from "./api";
import type { Dashboard, IdOption, Page } from "@/types/fleet";

export type Params = Record<string, string | number | undefined>;

const qs = (p: Params) => {
  const u = new URLSearchParams();
  Object.entries(p).forEach(([k, v]) => { if (v !== undefined && v !== "") u.set(k, String(v)); });
  const s = u.toString();
  return s ? `?${s}` : "";
};

/** Typed helpers for one backend collection, e.g. resource<Vehicle>("vehicles"). */
export const resource = <T>(path: string) => ({
  list: (p: Params) => api<Page<T>>(`/${path}${qs(p)}`),
  create: (body: unknown) => post<T>(`/${path}`, body),
  update: (id: string, body: unknown) => patch<T>(`/${path}/${id}`, body),
  remove: (id: string) => del(`/${path}/${id}`),
});

export const options = (path: "vehicles" | "drivers") => api<IdOption[]>(`/${path}/options`);
export const getDashboard = (days: number) => api<Dashboard>(`/dashboard?days=${days}`);
