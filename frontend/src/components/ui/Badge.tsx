import type { ReactNode } from "react";
import { cn } from "@/utils/cn";

const tone = { ok: "text-ok border-ok/40", warn: "text-warn border-warn/40", danger: "text-danger border-danger/40", info: "text-electric border-electric/40" };
export function Badge({ tone: t = "info", children }: { tone?: keyof typeof tone; children: ReactNode }) {
  return <span className={cn("inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium", tone[t])}>{children}</span>;
}
