import { Badge } from "@/components/ui";

export const titleCase = (s: string) => s.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase());

const TONES: Record<string, "ok" | "warn" | "danger" | "info"> = {
  active: "ok", available: "ok", delivered: "ok", completed: "ok",
  idle: "info", on_duty: "info", assigned: "info", in_transit: "info", scheduled: "info", preventive: "info", inspection: "info",
  pending: "warn", in_progress: "warn", maintenance: "warn", off_duty: "warn", on_leave: "warn", retired: "warn", repair: "warn",
  delayed: "danger", cancelled: "danger",
};
export function StatusBadge({ value }: { value: string }) {
  return <Badge tone={TONES[value] ?? "info"}>{titleCase(value)}</Badge>;
}

const parseDay = (iso: string) => { const [y, m, d] = iso.slice(0, 10).split("-").map(Number); return new Date(y, m - 1, d); };
export const fmtDate = (iso: string | null) => (iso ? parseDay(iso).toLocaleDateString() : "–");
export const fmtDateTime = (iso: string | null) => (iso ? new Date(iso).toLocaleString([], { dateStyle: "medium", timeStyle: "short" }) : "–");
export const fmtNum = (n: number | null | undefined, digits = 0) => (n === null || n === undefined ? "–" : n.toLocaleString(undefined, { minimumFractionDigits: digits, maximumFractionDigits: digits }));

export function daysUntil(iso: string): number {
  const t = new Date(); t.setHours(0, 0, 0, 0);
  return Math.round((parseDay(iso).getTime() - t.getTime()) / 86_400_000);
}

/** A date with an "Expired" / "N d left" badge when it is within 30 days. */
export function ExpiryText({ date }: { date: string | null }) {
  if (!date) return <span className="text-muted">–</span>;
  const d = daysUntil(date);
  return (
    <span className="inline-flex flex-wrap items-center gap-2">
      {fmtDate(date)}
      {d < 0 ? <Badge tone="danger">Expired</Badge> : d <= 30 ? <Badge tone="warn">{d}d left</Badge> : null}
    </span>
  );
}

/** ISO timestamp -> value for <input type="datetime-local"> in the browser's timezone. */
export function toLocalInput(iso: string): string {
  const d = new Date(iso);
  const p = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}`;
}
