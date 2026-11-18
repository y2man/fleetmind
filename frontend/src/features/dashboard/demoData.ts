export type VStatus = "active" | "idle" | "maintenance";
export interface Kpi { label: string; value: number; suffix?: string; decimals?: number }
export interface DashboardData {
  kpis: Kpi[];
  deliveries: { label: string; completed: number; delayed: number }[];
  fuel: { label: string; cost: number }[];
  vehicles: { id: string; x: number; y: number; status: VStatus }[];
  activity: { text: string; time: string }[];
  maintenance: { vehicle: string; task: string; due: string }[];
  insights: string[];
  alerts: { text: string; tone: "danger" | "warn" }[];
}

function rng(seed: number) { // mulberry32
  return () => { seed |= 0; seed = (seed + 0x6d2b79f5) | 0; let t = Math.imul(seed ^ (seed >>> 15), 1 | seed); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}

export function getDashboard(days: number): DashboardData {
  const r = rng(days * 97);
  const n = days <= 7 ? 7 : days <= 30 ? 10 : 12;
  const per = Math.max(1, Math.round(days / n));
  const deliveries = Array.from({ length: n }, (_, i) => { const c = Math.round((8 + r() * 8) * per); return { label: `P${i + 1}`, completed: c, delayed: Math.round(c * (0.04 + r() * 0.08)) }; });
  const fuel = Array.from({ length: n }, (_, i) => ({ label: `P${i + 1}`, cost: Math.round((300 + r() * 250) * per) }));
  const done = deliveries.reduce((s, d) => s + d.completed, 0);
  const late = deliveries.reduce((s, d) => s + d.delayed, 0);
  const total = 24, maint = 3, idle = 4, active = total - maint - idle;
  const status: VStatus[] = [...Array(active).fill("active"), ...Array(idle).fill("idle"), ...Array(maint).fill("maintenance")];
  return {
    kpis: [
      { label: "Total vehicles", value: total }, { label: "Active vehicles", value: active }, { label: "Available", value: idle }, { label: "In maintenance", value: maint },
      { label: "Active deliveries", value: 11 + Math.round(r() * 6) }, { label: "Completed deliveries", value: done }, { label: "Delayed deliveries", value: late }, { label: "Drivers", value: 18 },
      { label: "Fuel spend", value: fuel.reduce((s, f) => s + f.cost, 0) / 1000, suffix: "k", decimals: 1 },
      { label: "Fleet utilization", value: (active / total) * 100, suffix: "%", decimals: 1 },
      { label: "Delivery success", value: (1 - late / (done + late)) * 100, suffix: "%", decimals: 1 },
    ],
    deliveries, fuel,
    vehicles: status.map((s, i) => ({ id: `ET-${1001 + i}`, x: 40 + r() * 520, y: 30 + r() * 270, status: s })),
    activity: [
      { text: "ET-1004 completed delivery #D-2031", time: "4 min ago" }, { text: "ET-1011 left Depot A", time: "18 min ago" },
      { text: "Driver Hana T. started shift", time: "42 min ago" }, { text: "Fuel top-up logged for ET-1002", time: "1 h ago" },
    ],
    maintenance: [
      { vehicle: "ET-1002", task: "Oil change", due: "in 450 km" }, { vehicle: "ET-1006", task: "Brake inspection", due: "in 3 days" }, { vehicle: "ET-1013", task: "Tire rotation", due: "in 9 days" },
    ],
    insights: [
      "ET-1003 burns about 12% more fuel than similar trucks. Check tire pressure and routing.",
      "Two deliveries on the northern route are at risk of delay this afternoon.",
      "Moving ET-1005 from idle to the east route could save around 40 km per day.",
    ],
    alerts: [
      { text: "ET-1006 brake inspection is overdue soon", tone: "danger" },
      { text: "Delivery #D-2038 may miss its 16:00 deadline", tone: "warn" },
    ],
  };
}
