import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ClipboardCopy, FileText, Trash2 } from "lucide-react";
import { Badge, Button, Dropdown, GlassCard, Skeleton } from "@/components/ui";
import { FormError } from "@/features/auth/AuthLayout";
import { fmtDateTime } from "@/features/resource/format";
import { aiApi } from "@/services/ai";
import type { Report } from "@/types/ai";
import { RichText } from "./RichText";

const toText = (r: Report) =>
  [r.title, `Generated ${fmtDateTime(r.generated_at)}`, "", r.narrative ? `AI summary\n${r.narrative}\n` : "", ...r.sections.map((s) => `${s.heading}\n${s.bullets.map((b) => `- ${b}`).join("\n")}\n`)].join("\n");

export function ReportsPanel({ configured }: { configured: boolean }) {
  const qc = useQueryClient();
  const [days, setDays] = useState("30");
  const [selected, setSelected] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const list = useQuery({ queryKey: ["ai-reports"], queryFn: aiApi.reports });
  const detail = useQuery({ queryKey: ["ai-report", selected], queryFn: () => aiApi.report(selected as string), enabled: !!selected });
  const create = useMutation({
    mutationFn: () => aiApi.createReport(Number(days)),
    onSuccess: (r) => { if (r.id) { qc.setQueryData(["ai-report", r.id], r); setSelected(r.id); } qc.invalidateQueries({ queryKey: ["ai-reports"] }); },
  });
  const remove = useMutation({
    mutationFn: (id: string) => aiApi.deleteReport(id),
    onSuccess: (_, id) => { if (selected === id) setSelected(null); qc.invalidateQueries({ queryKey: ["ai-reports"] }); },
  });
  const report = detail.data;

  const copy = async () => {
    if (!report) return;
    try { await navigator.clipboard.writeText(toText(report)); setCopied(true); setTimeout(() => setCopied(false), 2000); } catch { /* clipboard blocked: nothing to do */ }
  };

  return (
    <div className="grid gap-4 lg:grid-cols-[18rem_1fr]">
      <GlassCard hover={false} className="space-y-4">
        <div>
          <h2 className="font-semibold">Executive report</h2>
          <p className="text-sm text-muted">Figures come straight from your records. {configured ? "A short written summary is added by AI." : "AI isn’t configured, so only the figures are included."}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Dropdown label="Period" value={days} onChange={setDays} options={[{ value: "7", label: "Last 7 days" }, { value: "30", label: "Last 30 days" }, { value: "90", label: "Last 90 days" }]} />
          <Button onClick={() => create.mutate()} disabled={create.isPending}><FileText size={16} />{create.isPending ? "Generating…" : "Generate"}</Button>
        </div>
        {create.isError && <FormError message={create.error.message} />}
        <div>
          <h3 className="mb-2 text-sm font-medium text-muted">Saved reports</h3>
          {list.isLoading ? <Skeleton className="h-16" /> : list.isError ? <FormError message={list.error.message} /> : list.data?.length === 0 ? <p className="text-sm text-muted">None yet.</p> : (
            <ul className="space-y-2">
              {list.data?.map((r) => (
                <li key={r.id} className="flex items-center gap-1">
                  <button onClick={() => setSelected(r.id)} aria-current={selected === r.id} className={`focus-ring flex-1 rounded-lg border px-3 py-2 text-left text-sm ${selected === r.id ? "border-electric" : "border-line"}`}>
                    {r.title}<span className="block text-xs text-muted">{fmtDateTime(r.generated_at)}{r.has_narrative ? " · AI summary" : ""}</span>
                  </button>
                  <Button size="sm" variant="ghost" aria-label={`Delete ${r.title}`} disabled={remove.isPending} onClick={() => { if (window.confirm("Delete this saved report?")) remove.mutate(r.id); }}><Trash2 size={16} /></Button>
                </li>
              ))}
            </ul>
          )}
          {remove.isError && <FormError message={remove.error.message} />}
        </div>
      </GlassCard>

      <GlassCard hover={false}>
        {!selected ? <p className="text-sm text-muted">Generate a report, or open a saved one.</p> : detail.isLoading ? <div className="space-y-3"><Skeleton className="h-8" /><Skeleton className="h-40" /></div> : detail.isError ? (
          <div className="space-y-2"><FormError message={detail.error.message} /><Button size="sm" variant="outline" onClick={() => detail.refetch()}>Try again</Button></div>
        ) : report && (
          <article className="space-y-5">
            <header className="flex flex-wrap items-start justify-between gap-2">
              <div><h2 className="text-xl font-bold">{report.title}</h2><p className="text-xs text-muted">Generated {fmtDateTime(report.generated_at)} · {String((report.facts.period as { start: string; end: string }).start)} to {String((report.facts.period as { start: string; end: string }).end)}</p></div>
              <Button size="sm" variant="outline" onClick={copy}><ClipboardCopy size={16} />{copied ? "Copied" : "Copy as text"}</Button>
            </header>
            {report.narrative ? (
              <section aria-label="AI summary" className="rounded-xl border border-electric/30 bg-electric/5 p-4">
                <p className="mb-2"><Badge tone="info">AI summary</Badge> <span className="text-xs text-muted">Written from the figures below only. Check anything important against them.</span></p>
                <RichText text={report.narrative} />
              </section>
            ) : report.narrative_note && <p role="status" className="rounded-lg border border-warn/40 bg-warn/10 px-3 py-2 text-sm text-warn">{report.narrative_note}</p>}
            {report.sections.map((s) => (
              <section key={s.heading}>
                <h3 className="mb-1 font-semibold">{s.heading}</h3>
                <ul className="list-disc space-y-1 pl-5 text-sm">{s.bullets.map((b, i) => <li key={i}>{b}</li>)}</ul>
              </section>
            ))}
          </article>
        )}
      </GlassCard>
    </div>
  );
}
