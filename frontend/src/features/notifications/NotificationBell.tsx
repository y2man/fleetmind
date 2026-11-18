import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Bell, CheckCheck, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui";
import type { AppNotification } from "@/types/analytics";
import { cn } from "@/utils/cn";
import { SEVERITY, safeLink, timeAgo } from "./format";
import { useNotifications } from "./useNotifications";

export function NotificationBell() {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const nav = useNavigate();
  const { list, refresh, read, readAll, enabled } = useNotifications(8);
  const unread = list.data?.unread_count ?? 0;

  useEffect(() => {
    if (!open) return;
    const click = (e: MouseEvent) => !ref.current?.contains(e.target as Node) && setOpen(false);
    const key = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("mousedown", click);
    document.addEventListener("keydown", key);
    return () => { document.removeEventListener("mousedown", click); document.removeEventListener("keydown", key); };
  }, [open]);

  if (!enabled) return null;

  const openItem = (n: AppNotification) => {
    if (!n.is_read) read.mutate(n.id);
    const to = safeLink(n.link);
    setOpen(false);
    if (to) nav(to);
  };

  return (
    <div ref={ref} className="relative">
      <button onClick={() => setOpen((o) => !o)} aria-haspopup="dialog" aria-expanded={open} aria-label={unread ? `Notifications, ${unread} unread` : "Notifications"}
        className="focus-ring glass relative rounded-xl p-2 hover:shadow-glow">
        <Bell size={18} />
        {unread > 0 && <span aria-hidden className="absolute -right-1 -top-1 grid min-h-4 min-w-4 place-items-center rounded-full bg-danger px-1 text-[10px] font-bold leading-none text-white">{unread > 99 ? "99+" : unread}</span>}
      </button>
      <AnimatePresence>
        {open && (
          <motion.div role="dialog" aria-label="Notifications" initial={{ opacity: 0, y: -6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -6 }}
            className="glass absolute right-0 z-40 mt-2 w-[min(24rem,calc(100vw-2rem))] rounded-2xl p-2">
            <div className="flex items-center justify-between px-2 py-1">
              <h2 className="text-sm font-semibold">Notifications</h2>
              <div className="flex gap-1">
                <Button variant="ghost" size="sm" onClick={() => refresh.mutate()} disabled={refresh.isPending} aria-label="Check for new alerts"><RefreshCw size={14} className={refresh.isPending ? "animate-spin" : ""} /></Button>
                <Button variant="ghost" size="sm" onClick={() => readAll.mutate()} disabled={unread === 0 || readAll.isPending}><CheckCheck size={14} />Mark all read</Button>
              </div>
            </div>
            {list.isError && <p role="alert" className="px-3 py-2 text-sm text-danger">Couldn’t load notifications. {list.error.message}</p>}
            {list.data && list.data.items.length === 0 && <p className="px-3 py-6 text-center text-sm text-muted">You’re all caught up. Expiring documents, overdue maintenance, late deliveries and unusual fuel use show up here.</p>}
            <ul className="max-h-96 overflow-y-auto">
              {list.data?.items.map((n) => {
                const sev = SEVERITY[n.severity];
                return (
                  <li key={n.id}>
                    <button onClick={() => openItem(n)} className="focus-ring flex w-full items-start gap-3 rounded-xl px-3 py-2 text-left hover:bg-electric/10">
                      <sev.icon size={16} className={cn("mt-0.5 shrink-0", sev.text)} aria-label={sev.label} />
                      <span className="min-w-0 flex-1">
                        <span className={cn("block text-sm", n.is_read ? "text-muted" : "font-medium")}>{n.title}</span>
                        {n.body && <span className="line-clamp-2 block text-xs text-muted">{n.body}</span>}
                        <span className="block text-xs text-muted">{timeAgo(n.created_at)}</span>
                      </span>
                      {!n.is_read && <span aria-label="Unread" className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-electric" />}
                    </button>
                  </li>
                );
              })}
            </ul>
            <div className="border-t border-line px-3 pt-2 text-right"><Link to="/app/notifications" onClick={() => setOpen(false)} className="text-sm text-electric underline">View all</Link></div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
