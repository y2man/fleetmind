import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Sparkles } from "lucide-react";
import { Badge, GlassCard, Skeleton } from "@/components/ui";
import { aiApi } from "@/services/ai";

type Row = { label: string; tab: string; flagged: number; detail: string };

/** Dashboard card: counts from the automatic checks. No language model is called to build it. */
export function AISummaryCard() {
  const q = useQuery({ queryKey: ["ai-summary"], queryFn: aiApi.summary, refetchInterval: 60_000 });
  const d = q.data;
  const rows: Row[] = d ? [
    ...(d.fuel_anomalies ? [{ label: "Fuel purchases to review", tab: "fuel", flagged: d.fuel_anomalies.critical + d.fuel_anomalies.warning, detail: `${d.fuel_anomalies.critical} critical, ${d.fuel_anomalies.warning} warnings (last 90 days)` }] : []),
    ...(d.delay_risk ? [{ label: "Deliveries late or at high risk", tab: "delays", flagged: d.delay_risk.late + d.delay_risk.high, detail: `${d.delay_risk.late} late, ${d.delay_risk.high} high risk` }] : []),
    ...(d.maintenance_risk ? [{ label: "Vehicles with high maintenance risk", tab: "maintenance", flagged: d.maintenance_risk.high, detail: `${d.maintenance_risk.high} high, ${d.maintenance_risk.medium} medium` }] : []),
  ] : [];
  return (
    <GlassCard hover={false}>
      <div className="mb-2 flex items-center justify-between gap-2">
        <h2 className="flex items-center gap-2 font-semibold"><Sparkles size={16} className="text-violet" />AI insights</h2>
        <Link className="text-sm text-electric underline" to="/app/ai">Open AI center</Link>
      </div>
      {q.isError ? <p className="text-sm text-danger" role="alert">{q.error.message}</p> : !d ? <Skeleton className="h-20" /> : (
        <ul className="grid gap-3 text-sm sm:grid-cols-3">
          {rows.map((r) => (
            <li key={r.tab}>
              <Link to={`/app/ai?tab=${r.tab}`} className="focus-ring block rounded-lg p-1 hover:bg-surface/70">
                <span className="text-2xl font-bold">{r.flagged}</span> <Badge tone={r.flagged ? "warn" : "ok"}>{r.flagged ? "Review" : "Clear"}</Badge>
                <span className="block">{r.label}</span><span className="block text-xs text-muted">{r.detail}</span>
              </Link>
            </li>
          ))}
        </ul>
      )}
      <p className="mt-2 text-xs text-muted">Automatic checks on your own records. They are flags to review, not conclusions.</p>
    </GlassCard>
  );
}
