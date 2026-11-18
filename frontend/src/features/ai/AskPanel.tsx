import { useEffect, useRef, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Send, Trash2 } from "lucide-react";
import { Button, GlassCard } from "@/components/ui";
import { titleCase } from "@/features/resource/format";
import { aiApi } from "@/services/ai";
import type { ChatTurn, ToolUsed } from "@/types/ai";
import { RichText } from "./RichText";

interface Turn extends ChatTurn { tools?: ToolUsed[]; error?: boolean }

const SAMPLES = [
  "Give me a summary of the fleet right now",
  "Which deliveries are at risk of being late?",
  "Which vehicles need maintenance soon?",
  "How much fuel did we buy in the last 30 days?",
  "Which drivers have the best on-time rate this month?",
  "Are any documents expiring in the next 30 days?",
  "Is there anything unusual in our fuel purchases?",
];
const TOOL_LABELS: Record<string, string> = {
  fleet_overview: "Fleet overview", search_vehicles: "Vehicles", search_drivers: "Drivers", search_deliveries: "Deliveries", fuel_summary: "Fuel totals",
  maintenance_overview: "Maintenance records", expiring_documents: "Document dates", driver_performance: "Driver on-time rates", fuel_anomalies: "Fuel screening",
  delivery_delay_risks: "Delivery risk screening", maintenance_forecast: "Maintenance forecast",
};

export function AskPanel({ configured }: { configured: boolean }) {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const end = useRef<HTMLDivElement>(null);

  const ask = useMutation({
    mutationFn: ({ q, history }: { q: string; history: ChatTurn[] }) => aiApi.ask(q, history),
    onSuccess: (r) => setTurns((t) => [...t, { role: "assistant", content: r.answer, tools: r.tools_used }]),
    onError: (e: Error) => setTurns((t) => [...t, { role: "assistant", content: e.message, error: true }]),
  });
  useEffect(() => { end.current?.scrollIntoView?.({ block: "nearest" }); }, [turns, ask.isPending]);

  const send = (text: string) => {
    const q = text.trim();
    if (!q || ask.isPending || !configured) return;
    // The server only accepts user/assistant text, so errors and tool details are not sent back.
    const history = turns.filter((t) => !t.error).slice(-10).map((t) => ({ role: t.role, content: t.content.slice(0, 4000) }));
    setTurns((t) => [...t, { role: "user", content: q }]);
    setInput("");
    ask.mutate({ q, history });
  };

  return (
    <GlassCard hover={false} className="flex flex-col gap-4">
      {!configured && <p role="status" className="rounded-lg border border-warn/40 bg-warn/10 px-3 py-2 text-sm text-warn">AI isn’t set up yet. Add <code>GROQ_API_KEY</code> to the backend <code>.env</code> and restart the backend. Fuel screening, delivery risks and maintenance forecasts below work without it.</p>}

      <div className="max-h-[28rem] min-h-[10rem] space-y-3 overflow-y-auto pr-1" aria-live="polite">
        {turns.length === 0 && (
          <div>
            <p className="mb-2 text-sm text-muted">Ask about your own fleet data. Try one of these:</p>
            <div className="flex flex-wrap gap-2">
              {SAMPLES.map((s) => <button key={s} disabled={!configured} onClick={() => send(s)} className="focus-ring rounded-full border border-line px-3 py-1.5 text-left text-sm hover:border-electric disabled:opacity-50">{s}</button>)}
            </div>
          </div>
        )}
        {turns.map((t, i) => (
          <div key={i} className={t.role === "user" ? "flex justify-end" : "flex justify-start"}>
            <div className={t.role === "user" ? "max-w-[85%] rounded-2xl bg-electric/15 px-4 py-2 text-sm" : t.error ? "max-w-[85%] rounded-2xl border border-danger/40 bg-danger/10 px-4 py-2 text-sm text-danger" : "glass max-w-[90%] rounded-2xl px-4 py-3"}>
              {t.role === "user" || t.error ? <span className="whitespace-pre-wrap">{t.content}</span> : <RichText text={t.content} />}
              {t.tools && (
                <details className="mt-2 text-xs text-muted">
                  <summary className="cursor-pointer">{t.tools.length ? `Data used (${t.tools.length})` : "No data was looked up for this answer"}</summary>
                  <ul className="mt-1 list-disc pl-5">{t.tools.map((u, j) => <li key={j}>{TOOL_LABELS[u.name] ?? titleCase(u.name)}{Object.keys(u.arguments).length ? `: ${JSON.stringify(u.arguments)}` : ""}</li>)}</ul>
                </details>
              )}
            </div>
          </div>
        ))}
        {ask.isPending && <p className="text-sm text-muted" role="status">Looking at your data…</p>}
        <div ref={end} />
      </div>

      <form onSubmit={(e) => { e.preventDefault(); send(input); }} className="flex items-end gap-2">
        <label className="sr-only" htmlFor="ai-question">Your question</label>
        <textarea id="ai-question" value={input} onChange={(e) => setInput(e.target.value)} maxLength={1000} rows={2} disabled={!configured}
          onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(input); } }}
          placeholder={configured ? "Ask a question about your fleet…" : "AI is not configured"}
          className="focus-ring w-full resize-none rounded-xl border border-line bg-bg/60 px-3 py-2 text-sm text-ink placeholder:text-muted/60 disabled:opacity-60" />
        <Button type="submit" disabled={!configured || ask.isPending || !input.trim()} aria-label="Send question"><Send size={16} /></Button>
        {turns.length > 0 && <Button type="button" variant="ghost" onClick={() => setTurns([])} aria-label="Clear conversation"><Trash2 size={16} /></Button>}
      </form>
    </GlassCard>
  );
}
