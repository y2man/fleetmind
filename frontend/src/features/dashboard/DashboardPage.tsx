import { useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { RefreshCw } from "lucide-react";
import { AnimatedNumber } from "@/components/animations/AnimatedNumber";
import { DeliveriesChart } from "@/components/charts/DeliveriesChart";
import { FuelChart } from "@/components/charts/FuelChart";
import { Badge, Button, Dropdown, GlassCard, Skeleton } from "@/components/ui";
import { FormError } from "@/features/auth/AuthLayout";
import { FleetMap } from "@/components/maps/FleetMap";
import { AISummaryCard } from "@/features/ai/AISummaryCard";
import { fmtDate, titleCase } from "@/features/resource/format";
import { getDashboard } from "@/services/resources";
import { trackingApi } from "@/services/tracking";
import { useAuth } from "@/store/auth";

const RANGES = [{ value: "7", label: "Last 7 days" }, { value: "30", label: "Last 30 days" }, { value: "90", label: "Last 90 days" }];
const STATUS_BAR: Record<string, string> = { active: "bg-ok", idle: "bg-electric", maintenance: "bg-warn", retired: "bg-muted" };

function timeAgo(iso: string): string {
  const s = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
  if (s < 60) return "just now";
  if (s < 3600) return `${Math.floor(s / 60)} min ago`;
  if (s < 86400) return `${Math.floor(s / 3600)} h ago`;
  return `${Math.floor(s / 86400)} d ago`;
}

export function DashboardPage() {
  const [range, setRange] = useState("30");
  const reduceMotion = useReducedMotion();
  const { can } = useAuth();
  const q = useQuery({ queryKey: ["dashboard", range], queryFn: () => getDashboard(Number(range)) });
  const d = q.data;
  const positions = useQuery({ queryKey: ["positions"], queryFn: trackingApi.positions, enabled: can("vehicles:read"), refetchInterval: 15_000 });
  const totalVehicles = d ? Object.values(d.vehicle_status).reduce((a, b) => a + b, 0) : 0;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div><h1 className="text-gradient text-3xl font-extrabold">Command center</h1><p className="text-muted">Live numbers from your organization’s data.</p></div>
        <div className="flex items-center gap-2">
          <Dropdown label="Date range" options={RANGES} value={range} onChange={setRange} />
          <Button variant="outline" size="sm" onClick={() => q.refetch()} aria-label="Refresh data"><RefreshCw size={16} className={q.isFetching ? "animate-spin" : ""} />Refresh</Button>
        </div>
      </div>

      {q.isError && <div className="space-y-2"><FormError message={q.error.message} /><Button variant="outline" size="sm" onClick={() => q.refetch()}>Try again</Button></div>}

      {d && !d.has_data && (
        <GlassCard hover={false}>
          <h2 className="font-semibold">Nothing here yet</h2>
          <p className="mt-1 text-sm text-muted">Add your first records and this page fills in. Start with{" "}
            {can("vehicles:write") ? <Link className="text-electric underline" to="/app/fleet">vehicles</Link> : "vehicles"}, then{" "}
            {can("drivers:write") ? <Link className="text-electric underline" to="/app/drivers">drivers</Link> : "drivers"} and{" "}
            {can("deliveries:write") ? <Link className="text-electric underline" to="/app/deliveries">deliveries</Link> : "deliveries"}.
          </p>
        </GlassCard>
      )}

      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-4">
        {!d ? Array.from({ length: 11 }, (_, i) => <Skeleton key={i} className="h-24" />) : d.kpis.map((k) => (
          <GlassCard key={k.key}>
            <p className="text-xs text-muted">{k.label}</p>
            <p className="mt-1 text-2xl font-bold">{k.value === null ? <span title="Not enough data yet">–</span> : <AnimatedNumber value={k.value} decimals={k.decimals} suffix={k.suffix} />}</p>
          </GlassCard>
        ))}
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <GlassCard hover={false}><h2 className="mb-2 font-semibold">Deliveries</h2>{d ? <DeliveriesChart data={d.deliveries} /> : <Skeleton className="h-60" />}</GlassCard>
        <GlassCard hover={false}><h2 className="mb-2 font-semibold">Fuel expenditure</h2>{d ? <FuelChart data={d.fuel} /> : <Skeleton className="h-60" />}</GlassCard>
      </div>

      {can("vehicles:read") && (
        <GlassCard hover={false} className="p-3">
          <div className="mb-2 flex flex-wrap items-center justify-between gap-2 px-2 pt-1">
            <h2 className="font-semibold">Fleet map <Badge tone="warn">Simulated GPS · demo</Badge></h2>
            <Link className="text-sm text-electric underline" to="/app/tracking">Open live map</Link>
          </div>
          {positions.isError ? <div className="space-y-2 p-2"><FormError message={positions.error.message} /><Button size="sm" variant="outline" onClick={() => positions.refetch()}>Try again</Button></div> : (
            <>
              <FleetMap className="h-72" vehicles={positions.data ?? []} />
              {positions.data && positions.data.length === 0 && <p className="px-2 pt-2 text-sm text-muted">No vehicle positions yet. Open the live map to start the simulation.</p>}
            </>
          )}
        </GlassCard>
      )}

      <div className="grid gap-4 lg:grid-cols-3">
        <GlassCard hover={false}>
          <h2 className="mb-3 font-semibold">Fleet status</h2>
          {!d ? <Skeleton className="h-24" /> : totalVehicles === 0 ? <p className="text-sm text-muted">No vehicles yet.</p> : (
            <ul className="space-y-3 text-sm">
              {Object.entries(d.vehicle_status).map(([s, n]) => (
                <li key={s}>
                  <div className="mb-1 flex justify-between"><span>{titleCase(s)}</span><span className="text-muted">{n}</span></div>
                  <div className="h-2 overflow-hidden rounded-full bg-line/50" role="img" aria-label={`${titleCase(s)}: ${n} of ${totalVehicles}`}>
                    <motion.div
                      initial={reduceMotion ? false : { width: 0 }}
                      animate={{ width: `${(n / totalVehicles) * 100}%` }}
                      transition={{ duration: reduceMotion ? 0 : 0.75, ease: [0.22, 1, 0.36, 1] }}
                      className={`h-full rounded-full ${STATUS_BAR[s] ?? "bg-electric"}`}
                    />
                  </div>
                </li>
              ))}
            </ul>
          )}
        </GlassCard>
        <GlassCard hover={false}>
          <h2 className="mb-2 font-semibold">Alerts</h2>
          {!d ? <Skeleton className="h-24" /> : d.alerts.length === 0 ? <p className="text-sm text-muted">No alerts. Expiring documents, overdue maintenance and late deliveries show up here.</p> : (
            <ul className="space-y-2">{d.alerts.map((a) => <li key={a.text}><Badge tone={a.severity === "critical" ? "danger" : "warn"}>{a.severity === "critical" ? "Critical" : "Warning"}</Badge> <span className="text-sm">{a.text}</span></li>)}</ul>
          )}
        </GlassCard>
        <GlassCard hover={false}>
          <h2 className="mb-2 font-semibold">Recent activity</h2>
          {!d ? <Skeleton className="h-24" /> : d.activity.length === 0 ? <p className="text-sm text-muted">No activity yet.</p> : (
            <ul className="space-y-2 text-sm">{d.activity.map((a, i) => <li key={i}>{a.text}<span className="block text-xs text-muted">{timeAgo(a.at)}</span></li>)}</ul>
          )}
        </GlassCard>
      </div>

      <GlassCard hover={false}>
        <h2 className="mb-2 font-semibold">Upcoming maintenance</h2>
        {!d ? <Skeleton className="h-16" /> : d.maintenance.length === 0 ? <p className="text-sm text-muted">Nothing scheduled.</p> : (
          <ul className="grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-3">
            {d.maintenance.map((m, i) => (
              <li key={i}><b>{m.vehicle}</b> · {m.task}
                <span className="block text-xs text-muted">{m.due ? fmtDate(m.due) : "No date"} {m.overdue && <Badge tone="danger">Overdue</Badge>}</span>
              </li>
            ))}
          </ul>
        )}
      </GlassCard>
      {can("ai:use") && <AISummaryCard />}
      {can("analytics:read") && <p className="text-xs text-muted">Need trends, exports or a PDF report? Open <Link className="text-electric underline" to="/app/analytics">Analytics</Link>. Alerts also appear in the bell at the top.</p>}
    </div>
  );
}
