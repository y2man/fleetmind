import { useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { ArrowDownRight, ArrowUpRight, FileText, Info, Minus, RefreshCw } from "lucide-react";
import { DeliveryTrendChart, SpendChart } from "@/components/charts/AnalyticsCharts";
import { Badge, Button, Dropdown, GlassCard, Skeleton } from "@/components/ui";
import { FormError } from "@/features/auth/AuthLayout";
import { StatusBadge, fmtDate, fmtNum, titleCase } from "@/features/resource/format";
import { analyticsApi } from "@/services/analytics";
import { useAuth } from "@/store/auth";
import type { AnalyticsKpi, RangeParams } from "@/types/analytics";
import { cn } from "@/utils/cn";

const PRESETS = [
  { value: "7", label: "Last 7 days" }, { value: "30", label: "Last 30 days" }, { value: "90", label: "Last 90 days" },
  { value: "180", label: "Last 6 months" }, { value: "365", label: "Last 12 months" }, { value: "custom", label: "Custom range…" },
];
const DATASETS = [
  { value: "deliveries", label: "Deliveries", perm: "deliveries:read" }, { value: "fuel", label: "Fuel purchases", perm: "fuel:read" },
  { value: "maintenance", label: "Maintenance", perm: "maintenance:read" }, { value: "vehicles", label: "Vehicles", perm: "vehicles:read" },
  { value: "drivers", label: "Drivers", perm: "drivers:read" },
];
const isoDay = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
// The server counts UTC days and rejects an end date after today (UTC), so the date inputs are capped at today's UTC date.
const todayUtc = () => new Date().toISOString().slice(0, 10);

function Change({ k }: { k: AnalyticsKpi }) {
  if (k.change_pct === null) return <span className="text-xs text-muted" title="The previous period has no data to compare with">no comparison</span>;
  if (k.change_pct === 0) return <span className="inline-flex items-center gap-1 text-xs text-muted"><Minus size={12} />no change</span>;
  const up = k.change_pct > 0;
  const improved = k.good === "neutral" ? null : (k.good === "up") === up;
  const tone = improved === null ? "text-muted" : improved ? "text-ok" : "text-danger";
  const Icon = up ? ArrowUpRight : ArrowDownRight;
  return <span className={cn("inline-flex items-center gap-1 text-xs", tone)}><Icon size={12} aria-hidden />{up ? "+" : ""}{k.change_pct.toFixed(1)}% <span className="text-muted">vs previous</span></span>;
}

export function AnalyticsPage() {
  const { can } = useAuth();
  const [preset, setPreset] = useState("30");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [applied, setApplied] = useState<{ start: string; end: string } | null>(null);
  const [dlError, setDlError] = useState<string | null>(null);

  const range: RangeParams | null = useMemo(() => {
    if (preset !== "custom") return { days: Number(preset) };
    return applied;
  }, [preset, applied]);
  const customInvalid = preset === "custom" && (!from || !to || from > to || to > todayUtc());

  const q = useQuery({ queryKey: ["analytics", range], queryFn: () => analyticsApi.get(range!), enabled: range !== null, placeholderData: (p) => p });
  const d = q.data;

  const csv = useMutation({ mutationFn: (dataset: string) => analyticsApi.csv(dataset, range!), onMutate: () => setDlError(null), onError: (e: Error) => setDlError(e.message) });
  const pdf = useMutation({ mutationFn: () => analyticsApi.pdf(range!), onMutate: () => setDlError(null), onError: (e: Error) => setDlError(e.message) });
  const busy = csv.isPending || pdf.isPending;
  const datasets = DATASETS.filter((x) => can(x.perm));
  const maxStatus = Math.max(1, ...(d?.delivery_status.map((s) => s.count) ?? [1]));

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-gradient text-3xl font-extrabold">Analytics</h1>
          <p className="text-muted">{d ? <>{fmtDate(d.range.start)} to {fmtDate(d.range.end)} · {d.range.days} days (UTC)</> : "Trends, costs and driver performance."}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Dropdown label="Date range" options={PRESETS} value={preset} onChange={(v) => { setPreset(v); if (v === "custom" && !from) { const t = new Date(); const s = new Date(); s.setDate(t.getDate() - 29); setFrom(isoDay(s)); setTo(todayUtc()); } }} />
          <Button variant="outline" size="sm" onClick={() => q.refetch()} disabled={range === null} aria-label="Refresh data"><RefreshCw size={16} className={q.isFetching ? "animate-spin" : ""} />Refresh</Button>
          {datasets.length > 0 && <Dropdown label="Export CSV" options={datasets.map(({ value, label }) => ({ value, label }))} value="" onChange={(v) => range && csv.mutate(v)} />}
          <Button variant="outline" size="sm" onClick={() => pdf.mutate()} disabled={busy || range === null}><FileText size={16} />{pdf.isPending ? "Preparing…" : "PDF report"}</Button>
        </div>
      </div>

      {preset === "custom" && (
        <GlassCard hover={false} className="flex flex-wrap items-end gap-3">
          <label className="space-y-1 text-sm text-muted">From<input type="date" value={from} max={todayUtc()} onChange={(e) => setFrom(e.target.value)} className="focus-ring block rounded-xl border border-line bg-bg/60 px-3 py-2 text-ink" /></label>
          <label className="space-y-1 text-sm text-muted">To<input type="date" value={to} max={todayUtc()} onChange={(e) => setTo(e.target.value)} className="focus-ring block rounded-xl border border-line bg-bg/60 px-3 py-2 text-ink" /></label>
          <Button size="sm" disabled={customInvalid} onClick={() => setApplied({ start: from, end: to })}>Apply</Button>
          <p className="text-xs text-muted">{customInvalid && from && to ? (from > to ? "The start date must not be after the end date." : "The end date cannot be in the future.") : "Up to 366 days."}</p>
        </GlassCard>
      )}
      {preset === "custom" && range === null && <p className="text-sm text-muted">Pick two dates and press Apply.</p>}

      {dlError && <FormError message={`Download failed: ${dlError}`} />}
      {q.isError && <div className="space-y-2"><FormError message={q.error.message} /><Button variant="outline" size="sm" onClick={() => q.refetch()}>Try again</Button></div>}
      {d && !d.has_data && <GlassCard hover={false}><p className="text-sm text-muted">There is no activity in this range yet. Try a longer range, or add deliveries, fuel purchases and maintenance records.</p></GlassCard>}

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {!d ? Array.from({ length: 8 }, (_, i) => <Skeleton key={i} className="h-24" />) : d.kpis.map((k) => (
          <GlassCard key={k.key}>
            <p className="text-xs text-muted">{k.label}</p>
            <p className="mt-1 text-2xl font-bold">{k.value === null ? <span title="Not enough data in this range">–</span> : `${fmtNum(k.value, k.decimals)}${k.suffix}`}</p>
            <Change k={k} />
          </GlassCard>
        ))}
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <GlassCard hover={false}><h2 className="mb-2 font-semibold">Deliveries over time</h2>{d ? <DeliveryTrendChart data={d.series} /> : <Skeleton className="h-64" />}</GlassCard>
        <GlassCard hover={false}><h2 className="mb-2 font-semibold">Fuel and maintenance spend</h2>{d ? <SpendChart data={d.series} /> : <Skeleton className="h-64" />}</GlassCard>
      </div>
      {d && d.range.bucket_days > 1 && <p className="text-xs text-muted">Charts group {d.range.bucket_days} days per point; each point is labeled with its first day.</p>}

      <div className="grid gap-4 lg:grid-cols-3">
        <GlassCard hover={false}>
          <h2 className="mb-1 font-semibold">Delivery status</h2><p className="mb-3 text-xs text-muted">Deliveries created in this range</p>
          {!d ? <Skeleton className="h-24" /> : d.delivery_status.length === 0 ? <p className="text-sm text-muted">No deliveries created in this range.</p> : (
            <ul className="space-y-3 text-sm">{d.delivery_status.map((s) => (
              <li key={s.status}>
                <div className="mb-1 flex justify-between"><StatusBadge value={s.status} /><span className="text-muted">{s.count}</span></div>
                <div className="h-2 overflow-hidden rounded-full bg-line/50" role="img" aria-label={`${titleCase(s.status)}: ${s.count}`}><div className="h-full rounded-full bg-electric" style={{ width: `${(s.count / maxStatus) * 100}%` }} /></div>
              </li>
            ))}</ul>
          )}
        </GlassCard>
        <GlassCard hover={false} className="overflow-x-auto lg:col-span-2">
          <h2 className="mb-2 font-semibold">Fuel by vehicle <span className="text-xs font-normal text-muted">(top 10 by cost)</span></h2>
          {!d ? <Skeleton className="h-24" /> : d.fuel_by_vehicle.length === 0 ? <p className="text-sm text-muted">No fuel purchases in this range.</p> : (
            <table className="w-full text-sm"><thead><tr className="text-left text-xs text-muted"><th className="py-1 pr-3 font-medium">Vehicle</th><th className="py-1 pr-3 text-right font-medium">Fills</th><th className="py-1 pr-3 text-right font-medium">Liters</th><th className="py-1 pr-3 text-right font-medium">Cost</th><th className="py-1 text-right font-medium">Cost / L</th></tr></thead>
              <tbody>{d.fuel_by_vehicle.map((r) => <tr key={r.vehicle} className="border-t border-line"><td className="py-1.5 pr-3 font-medium">{r.vehicle}</td><td className="py-1.5 pr-3 text-right">{r.fills}</td><td className="py-1.5 pr-3 text-right">{fmtNum(r.liters, 1)}</td><td className="py-1.5 pr-3 text-right">{fmtNum(r.cost, 2)}</td><td className="py-1.5 text-right">{fmtNum(r.cost_per_liter, 3)}</td></tr>)}</tbody></table>
          )}
        </GlassCard>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <GlassCard hover={false} className="overflow-x-auto lg:col-span-2">
          <h2 className="mb-2 font-semibold">Driver on-time performance <span className="text-xs font-normal text-muted">(top 10 by deliveries completed)</span></h2>
          {!d ? <Skeleton className="h-24" /> : d.drivers.length === 0 ? <p className="text-sm text-muted">No completed deliveries with a driver in this range.</p> : (
            <table className="w-full text-sm"><thead><tr className="text-left text-xs text-muted"><th className="py-1 pr-3 font-medium">Driver</th><th className="py-1 pr-3 text-right font-medium">Completed</th><th className="py-1 pr-3 text-right font-medium">On time</th><th className="py-1 pr-3 text-right font-medium">Late</th><th className="py-1 text-right font-medium">On-time rate</th></tr></thead>
              <tbody>{d.drivers.map((r) => <tr key={r.driver} className="border-t border-line"><td className="py-1.5 pr-3 font-medium">{r.driver}</td><td className="py-1.5 pr-3 text-right">{r.delivered}</td><td className="py-1.5 pr-3 text-right">{r.on_time}</td><td className="py-1.5 pr-3 text-right">{r.late}</td><td className="py-1.5 text-right">{r.on_time_rate_pct === null ? <span title="None of this driver's deliveries had a deadline">–</span> : <Badge tone={r.on_time_rate_pct >= 90 ? "ok" : r.on_time_rate_pct >= 70 ? "warn" : "danger"}>{r.on_time_rate_pct}%</Badge>}</td></tr>)}</tbody></table>
          )}
        </GlassCard>
        <GlassCard hover={false}>
          <h2 className="mb-2 font-semibold">Completed maintenance</h2>
          {!d ? <Skeleton className="h-24" /> : d.maintenance_by_kind.length === 0 ? <p className="text-sm text-muted">No maintenance completed in this range.</p> : (
            <ul className="space-y-2 text-sm">{d.maintenance_by_kind.map((m) => <li key={m.kind} className="flex justify-between"><span>{titleCase(m.kind)} <span className="text-muted">({m.count})</span></span><span>{fmtNum(m.cost, 2)}</span></li>)}</ul>
          )}
        </GlassCard>
      </div>

      {d && (
        <GlassCard hover={false}>
          <h2 className="mb-2 flex items-center gap-2 font-semibold"><Info size={16} aria-hidden />About these numbers</h2>
          <ul className="list-disc space-y-1 pl-5 text-sm text-muted">{d.notes.map((n) => <li key={n}>{n}</li>)}</ul>
        </GlassCard>
      )}
    </div>
  );
}
