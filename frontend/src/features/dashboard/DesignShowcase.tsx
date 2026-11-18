import { useState } from "react";
import { AnimatedNumber } from "@/components/animations/AnimatedNumber";
import { Badge, Button, Dropdown, GlassCard, Input, Modal, Skeleton } from "@/components/ui";

const range = [{ value: "7", label: "Last 7 days" }, { value: "30", label: "Last 30 days" }, { value: "90", label: "Last 90 days" }];

export function DesignShowcase() {
  const [open, setOpen] = useState(false);
  const [r, setR] = useState("30");
  const [loading, setLoading] = useState(false);
  const reload = () => { setLoading(true); setTimeout(() => setLoading(false), 1500); };
  return (
    <div className="space-y-6">
      <div><h1 className="text-gradient text-3xl font-extrabold">Design system</h1><p className="text-muted">Reusable building blocks for every FleetMind module.</p></div>
      <div className="grid gap-4 sm:grid-cols-3">
        {[["Active vehicles", 18, 0, ""], ["Delivery success", 96.4, 1, "%"], ["Fuel spend", 12.8, 1, "k"]].map(([l, v, d, s]) => (
          <GlassCard key={l as string}><p className="text-sm text-muted">{l}</p><p className="text-3xl font-bold"><AnimatedNumber value={v as number} decimals={d as number} suffix={s as string} /></p></GlassCard>
        ))}
      </div>
      <GlassCard hover={false} className="space-y-4">
        <h2 className="font-semibold">Controls</h2>
        <div className="flex flex-wrap items-center gap-3">
          <Button onClick={() => setOpen(true)}>Open modal</Button>
          <Button variant="outline" onClick={reload}>Show skeletons</Button>
          <Button variant="ghost">Ghost</Button>
          <Button variant="danger" size="sm">Danger</Button>
          <Dropdown label="Date range" options={range} value={r} onChange={setR} />
          <Badge tone="ok">Active</Badge><Badge tone="warn">Maintenance</Badge><Badge tone="danger">Delayed</Badge>
        </div>
        <div className="max-w-sm"><Input label="Vehicle registration" placeholder="ET-1001" /></div>
      </GlassCard>
      <GlassCard hover={false}>
        <h2 className="mb-3 font-semibold">Loading state</h2>
        {loading ? <div className="space-y-2"><Skeleton className="h-5 w-1/2" /><Skeleton className="h-5 w-full" /><Skeleton className="h-5 w-3/4" /></div> : <p className="text-muted">Press “Show skeletons” to preview the loader.</p>}
      </GlassCard>
      <Modal open={open} onClose={() => setOpen(false)} title="Example modal">
        <p className="mb-4 text-muted">Closes with Esc, the X button, or a click outside.</p>
        <Button onClick={() => setOpen(false)}>Done</Button>
      </Modal>
    </div>
  );
}
