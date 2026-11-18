import { AlertTriangle, Info, OctagonAlert, type LucideIcon } from "lucide-react";
import type { AppNotification } from "@/types/analytics";

export const SEVERITY: Record<AppNotification["severity"], { label: string; icon: LucideIcon; text: string }> = {
  critical: { label: "Critical", icon: OctagonAlert, text: "text-danger" },
  warning: { label: "Warning", icon: AlertTriangle, text: "text-warn" },
  info: { label: "Info", icon: Info, text: "text-electric" },
};

export function timeAgo(iso: string): string {
  const s = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
  if (s < 60) return "just now";
  if (s < 3600) return `${Math.floor(s / 60)} min ago`;
  if (s < 86400) return `${Math.floor(s / 3600)} h ago`;
  return `${Math.floor(s / 86400)} d ago`;
}

/** Notification links come from the server; only in-app paths are followed. */
export const safeLink = (link: string | null): string | null => (link && link.startsWith("/app/") ? link : null);
