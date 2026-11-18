import type { ReactNode } from "react";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Badge, Button, Dropdown, GlassCard, Skeleton } from "@/components/ui";
import { FormError } from "@/features/auth/AuthLayout";
import { fmtDate, fmtDateTime, fmtNum, titleCase } from "@/features/resource/format";
import { aiApi } from "@/services/ai";
import type { RiskLevel, Severity } from "@/types/ai";

const SEV_TONE: Record<Severity, "danger" | "warn" | "info"> = { critical: "danger", warning: "warn", info: "info" };
const LEVEL_TONE: Record<RiskLevel, "danger" | "warn" | "info" | "ok"> = { late: "danger", high: "danger", medium: "warn", low: "ok" };

function Loading({ error, retry }: { error?: Error | null; retry: () => void }) {
  return error ? <div className="space-y-2"><FormError message={error.message} /><Button size="sm" variant="outline" onClick={retry}>Try again</Button></div> : <div className="space-y-3"><Skeleton className="h-20" /><Skeleton className="h-20" /></div>;
}

function Method({ title = "How this works", lines }: { title?: string; lines: string[] }) {
  return (
    <details className="text-sm text-muted">
      <summary className="cursor-pointer">{title}</summary>
      <ul className="mt-2 list-disc space-y-1 pl-5">{lines.map((l) => <li key={l}>{l}</li>)}</ul>
    </details>
  );
}

function Counts({ items }: { items: { label: string; n: number; tone: "danger" | "warn" | "info" | "ok" }[] }) {
  return <div className="flex flex-wrap gap-2">{items.map((c) => <Badge key={c.label} tone={c.n ? c.tone : "info"}>{c.n} {c.label}</Badge>)}</div>;
}

const Item = ({ children }: { children: ReactNode }) => <li className="glass rounded-xl p-4">{children}</li>;

export function AnomaliesPanel() {
  const [days, setDays] = useState("90");
  const q = useQuery({ queryKey: ["ai-anomalies", days], queryFn: () => aiApi.anomalies(Number(days)) });
  const d = q.data;
  return (
    <GlassCard hover={false} className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div><h2 className="font-semibold">Fuel anomaly screening</h2><p className="text-sm text-muted">Unusual consumption, fill sizes, prices and data errors. These are flags to check, not proof of a problem.</p></div>
        <Dropdown label="Period" value={days} onChange={setDays} options={[{ value: "30", label: "Last 30 days" }, { value: "90", label: "Last 90 days" }, { value: "180", label: "Last 180 days" }, { value: "365", label: "Last 365 days" }]} />
      </div>
      {!d ? <Loading error={q.error} retry={q.refetch} /> : (
        <>
          <Counts items={[{ label: "critical", n: d.counts.critical, tone: "danger" }, { label: "warnings", n: d.counts.warning, tone: "warn" }, { label: "info", n: d.counts.info, tone: "info" }]} />
          {d.stats.transactions === 0 && <p className="text-sm text-muted">No fuel purchases are recorded yet. Add some on the Fuel page, with odometer readings, to enable screening.</p>}
          {d.items.length === 0 && d.stats.transactions > 0 && <p className="text-sm text-muted">Nothing unusual found by these checks in the last {d.days} days.</p>}
          {d.stats.not_enough_history > 0 && <p className="text-sm text-muted">{d.stats.not_enough_history} vehicle(s) have too few fill-ups with odometer readings for a consumption check (at least 6 purchases are needed).</p>}
          <ul className="space-y-3">
            {d.items.map((a) => (
              <Item key={a.id}>
                <div className="flex flex-wrap items-center gap-2"><Badge tone={SEV_TONE[a.severity]}>{titleCase(a.severity)}</Badge><b>{a.title}</b><span className="text-xs text-muted">{a.registration} · {fmtDateTime(a.occurred_at)}</span></div>
                <p className="mt-1 text-sm">{a.detail}</p>
                <details className="mt-1 text-xs text-muted"><summary className="cursor-pointer">Numbers behind this flag</summary>
                  <dl className="mt-1 grid grid-cols-2 gap-x-4 sm:grid-cols-3">{Object.entries(a.evidence).map(([k, v]) => <div key={k}><dt className="inline">{titleCase(k)}: </dt><dd className="inline text-ink">{String(v)}</dd></div>)}</dl>
                </details>
              </Item>
            ))}
          </ul>
          <Method lines={[...d.methods, ...d.limitations]} />
        </>
      )}
    </GlassCard>
  );
}

function minutesText(m: number): string {
  const a = Math.abs(m);
  const t = a >= 120 ? `${Math.floor(a / 60)} h ${a % 60} min` : `${a} min`;
  return m < 0 ? `${t} overdue` : `${t} left`;
}

export function DelayPanel() {
  const q = useQuery({ queryKey: ["ai-delay"], queryFn: aiApi.delayRisks });
  const d = q.data;
  return (
    <GlassCard hover={false} className="space-y-4">
      <div><h2 className="font-semibold">Delivery delay risk</h2><p className="text-sm text-muted">Open deliveries ranked by how likely they are to miss their deadline. This is a rule-based score, not a trained model.</p></div>
      {!d ? <Loading error={q.error} retry={q.refetch} /> : (
        <>
          <Counts items={[{ label: "late", n: d.counts.late, tone: "danger" }, { label: "high", n: d.counts.high, tone: "danger" }, { label: "medium", n: d.counts.medium, tone: "warn" }, { label: "low", n: d.counts.low, tone: "ok" }]} />
          {d.open_deliveries === 0 && <p className="text-sm text-muted">No open deliveries with deadlines to assess.</p>}
          {d.without_deadline > 0 && <p className="text-sm text-muted">{d.without_deadline} open deliveries have no deadline and can’t be assessed.</p>}
          <ul className="space-y-3">
            {d.items.map((r) => (
              <Item key={r.delivery_id}>
                <div className="flex flex-wrap items-center gap-2">
                  <Badge tone={LEVEL_TONE[r.level]}>{r.level === "late" ? "Late" : `${titleCase(r.level)} risk`}</Badge><b>{r.reference}</b>
                  <span className="text-xs text-muted">{titleCase(r.status)} · due {fmtDateTime(r.deadline)} · {minutesText(r.minutes_left)}{r.level !== "late" && ` · score ${r.score}`}</span>
                </div>
                <p className="mt-1 text-xs text-muted">To {r.dest_address}{r.vehicle ? ` · ${r.vehicle}` : " · no vehicle"}{r.driver ? ` · ${r.driver}` : " · no driver"}{r.estimated_trip_minutes !== null && ` · est. trip ${r.estimated_trip_minutes} min`}</p>
                {r.reasons.length > 0 ? <ul className="mt-1 list-disc pl-5 text-sm">{r.reasons.map((x) => <li key={x}>{x}</li>)}</ul> : <p className="mt-1 text-sm text-muted">No risk factors found.</p>}
              </Item>
            ))}
          </ul>
          <Method lines={[...d.methods, `Trip estimate defaults: road factor ${d.assumptions.road_factor}, ${d.assumptions.avg_speed_kph} km/h, ${d.assumptions.stop_minutes} min per stop.`]} />
        </>
      )}
    </GlassCard>
  );
}

export function MaintenancePanel() {
  const [interval, setIntervalKm] = useState("10000");
  const q = useQuery({ queryKey: ["ai-maint", interval], queryFn: () => aiApi.maintenance(Number(interval)) });
  const d = q.data;
  return (
    <GlassCard hover={false} className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div><h2 className="font-semibold">Maintenance forecast</h2><p className="text-sm text-muted">Vehicles likely to need service soon, from overdue jobs, kilometres since the last service and repair frequency.</p></div>
        <Dropdown label="Service interval" value={interval} onChange={setIntervalKm} options={[5000, 10000, 15000, 20000].map((n) => ({ value: String(n), label: `Every ${fmtNum(n)} km` }))} />
      </div>
      {!d ? <Loading error={q.error} retry={q.refetch} /> : (
        <>
          <Counts items={[{ label: "high", n: d.counts.high, tone: "danger" }, { label: "medium", n: d.counts.medium, tone: "warn" }, { label: "low", n: d.counts.low, tone: "info" }]} />
          {d.items.length === 0 && <p className="text-sm text-muted">No vehicles are flagged. Mileage-based checks need a completed preventive service with an odometer reading on the Maintenance page.</p>}
          <ul className="space-y-3">
            {d.items.map((m) => (
              <Item key={m.vehicle_id}>
                <div className="flex flex-wrap items-center gap-2"><Badge tone={LEVEL_TONE[m.risk]}>{titleCase(m.risk)} risk</Badge><b>{m.registration}</b><span className="text-xs text-muted">{m.label} · {fmtNum(m.current_km)} km{m.km_per_day ? ` · about ${fmtNum(m.km_per_day)} km/day` : ""}</span></div>
                <ul className="mt-1 list-disc pl-5 text-sm">{m.reasons.map((x) => <li key={x}>{x}</li>)}</ul>
                {m.predicted_due_date && <p className="mt-1 text-xs text-muted">Estimated service date: {fmtDate(m.predicted_due_date)} (an estimate from recent distance driven)</p>}
              </Item>
            ))}
          </ul>
          <Method lines={d.methods} />
        </>
      )}
    </GlassCard>
  );
}
