import { useQuery } from "@tanstack/react-query";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { useSearchParams } from "react-router-dom";
import { aiApi } from "@/services/ai";
import { cn } from "@/utils/cn";
import { AskPanel } from "./AskPanel";
import { ReportsPanel } from "./ReportsPanel";
import { AnomaliesPanel, DelayPanel, MaintenancePanel } from "./Screening";

const TABS = [
  { id: "ask", label: "Ask" },
  { id: "fuel", label: "Fuel anomalies" },
  { id: "delays", label: "Delay risk" },
  { id: "maintenance", label: "Maintenance" },
  { id: "reports", label: "Reports" },
] as const;
type TabId = (typeof TABS)[number]["id"];

export function AIPage() {
  const [params, setParams] = useSearchParams();
  const reduceMotion = useReducedMotion();
  const requested = params.get("tab");
  const tab: TabId = TABS.some((t) => t.id === requested) ? (requested as TabId) : "ask";
  const health = useQuery({ queryKey: ["health"], queryFn: aiApi.health });
  const configured = health.data?.ai_configured ?? false;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-gradient text-3xl font-extrabold">AI center</h1>
        <p className="text-muted">Ask questions in plain language and review automatic checks on your real data.</p>
      </div>

      <div role="tablist" aria-label="AI center sections" className="flex flex-wrap gap-2">
        {TABS.map((t) => (
          <motion.button key={t.id} role="tab" id={`tab-${t.id}`} aria-selected={tab === t.id} aria-controls={`panel-${t.id}`} onClick={() => setParams({ tab: t.id }, { replace: true })}
            whileTap={reduceMotion ? undefined : { scale: 0.96 }}
            className={cn("focus-ring relative isolate overflow-hidden rounded-xl border px-4 py-2 text-sm font-medium transition-colors", tab === t.id ? "border-electric/50 text-ink" : "border-line text-muted hover:text-ink")}>
            {tab === t.id && <motion.span layoutId="ai-center-tab" className="absolute inset-0 -z-10 rounded-xl bg-electric/10" transition={{ type: "spring", stiffness: 360, damping: 30 }} />}
            <span className="relative">{t.label}</span>
          </motion.button>
        ))}
      </div>

      <div role="tabpanel" id={`panel-${tab}`} aria-labelledby={`tab-${tab}`}>
        <AnimatePresence mode="wait" initial={false}>
          <motion.div
            key={tab}
            initial={reduceMotion ? false : { opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={reduceMotion ? undefined : { opacity: 0, y: -8 }}
            transition={{ duration: reduceMotion ? 0 : 0.24, ease: "easeOut" }}
          >
            {tab === "ask" && <AskPanel configured={configured} />}
            {tab === "fuel" && <AnomaliesPanel />}
            {tab === "delays" && <DelayPanel />}
            {tab === "maintenance" && <MaintenancePanel />}
            {tab === "reports" && <ReportsPanel configured={configured} />}
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  );
}
