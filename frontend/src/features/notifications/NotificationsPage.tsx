import { useState } from "react";
import { Link } from "react-router-dom";
import { CheckCheck, RefreshCw } from "lucide-react";
import { Badge, Button, Dropdown, GlassCard, Skeleton } from "@/components/ui";
import { FormError } from "@/features/auth/AuthLayout";
import { fmtDateTime } from "@/features/resource/format";
import { cn } from "@/utils/cn";
import { SEVERITY, safeLink } from "./format";
import { useNotifications } from "./useNotifications";

const FILTERS = [{ value: "all", label: "All" }, { value: "unread", label: "Unread only" }];
const TONE = { critical: "danger", warning: "warn", info: "info" } as const;

export function NotificationsPage() {
  const [filter, setFilter] = useState("all");
  const { list, refresh, read, readAll } = useNotifications(100, filter === "unread");
  const d = list.data;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div><h1 className="text-gradient text-3xl font-extrabold">Notifications</h1><p className="text-muted">Smart alerts from your records: expiring documents, overdue maintenance, late deliveries and unusual fuel use.</p></div>
        <div className="flex flex-wrap items-center gap-2">
          <Dropdown label="Show" options={FILTERS} value={filter} onChange={setFilter} />
          <Button variant="outline" size="sm" onClick={() => refresh.mutate()} disabled={refresh.isPending}><RefreshCw size={16} className={refresh.isPending ? "animate-spin" : ""} />Check now</Button>
          <Button variant="outline" size="sm" onClick={() => readAll.mutate()} disabled={!d || d.unread_count === 0 || readAll.isPending}><CheckCheck size={16} />Mark all read</Button>
        </div>
      </div>

      {refresh.isSuccess && <p role="status" className="text-sm text-muted">{refresh.data.created === 0 ? "No new alerts." : `${refresh.data.created} new alert${refresh.data.created === 1 ? "" : "s"} found.`}</p>}
      {(refresh.isError || read.isError || readAll.isError) && <FormError message={(refresh.error ?? read.error ?? readAll.error)?.message} />}
      {list.isError && <div className="space-y-2"><FormError message={list.error.message} /><Button variant="outline" size="sm" onClick={() => list.refetch()}>Try again</Button></div>}

      <GlassCard hover={false} className="p-2">
        {!d ? <Skeleton className="h-40" /> : d.items.length === 0 ? (
          <p className="p-6 text-center text-sm text-muted">{filter === "unread" ? "Nothing unread." : "No notifications yet. Press “Check now” to run the alert rules."}</p>
        ) : (
          <ul className="divide-y divide-line">
            {d.items.map((n) => {
              const to = safeLink(n.link);
              return (
                <li key={n.id} className="flex flex-wrap items-start gap-3 px-3 py-3">
                  <Badge tone={TONE[n.severity]}>{SEVERITY[n.severity].label}</Badge>
                  <div className="min-w-0 flex-1">
                    <p className={cn("text-sm", n.is_read ? "text-muted" : "font-medium")}>{n.title}</p>
                    {n.body && <p className="text-sm text-muted">{n.body}</p>}
                    <p className="mt-0.5 text-xs text-muted">{fmtDateTime(n.created_at)}</p>
                  </div>
                  <div className="flex gap-2">
                    {to && <Link to={to} onClick={() => !n.is_read && read.mutate(n.id)} className="text-sm text-electric underline">Open</Link>}
                    {!n.is_read && <Button variant="ghost" size="sm" onClick={() => read.mutate(n.id)} disabled={read.isPending}>Mark read</Button>}
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </GlassCard>
      {d && <p className="text-xs text-muted">{d.unread_count} unread. Each condition is raised once, so a read alert does not come back unless the underlying fact changes (for example a new expiry date).</p>}
    </div>
  );
}
