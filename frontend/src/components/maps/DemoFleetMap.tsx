import type { DashboardData } from "@/features/dashboard/demoData";

const fill = { active: "#2fe0a0", idle: "#8e98c9", maintenance: "#ffc04d" } as const;
export function DemoFleetMap({ vehicles }: { vehicles: DashboardData["vehicles"] }) {
  return (
    <svg viewBox="0 0 600 330" role="img" aria-label="Simulated fleet map" className="w-full rounded-xl bg-bg/60">
      <path d="M0 170 Q150 100 300 180 T600 150" stroke="#4d8dff66" fill="none" strokeWidth="3" />
      <circle cx="300" cy="170" r="70" fill="none" stroke="#9b6bffaa" strokeDasharray="6" />
      {vehicles.map((v) => <circle key={v.id} cx={v.x} cy={v.y} r="6" fill={fill[v.status]}><title>{`${v.id} · ${v.status}`}</title></circle>)}
    </svg>
  );
}
