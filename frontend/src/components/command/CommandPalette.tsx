import { AnimatePresence, motion } from "framer-motion";
import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useRef, useState, type KeyboardEvent as ReactKeyboardEvent, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { Contact, CornerDownLeft, Keyboard, LogOut, Moon, Package, Search, Truck, type LucideIcon } from "lucide-react";
import { NAV } from "@/config/nav";
import { useDebounced } from "@/hooks/useDebounced";
import { searchApi } from "@/services/analytics";
import { useAuth } from "@/store/auth";
import { useTheme } from "@/store/theme";
import { useUi } from "@/store/ui";
import type { SearchHit } from "@/types/analytics";
import { cn } from "@/utils/cn";

interface Item { id: string; group: string; label: string; hint?: string; icon: LucideIcon; run: () => void }
const HIT_ICON: Record<SearchHit["type"], LucideIcon> = { vehicle: Truck, driver: Contact, delivery: Package };

/** Ctrl/Cmd+K palette: jump to pages, run a few commands, and search vehicles, drivers and deliveries. */
export function CommandPalette() {
  const { paletteOpen, setPalette, setHelp } = useUi();
  const { can, logout } = useAuth();
  const toggleTheme = useTheme((s) => s.toggle);
  const navigate = useNavigate();
  const [text, setText] = useState("");
  const [active, setActive] = useState(0);
  const input = useRef<HTMLInputElement>(null);
  const list = useRef<HTMLUListElement>(null);
  const term = useDebounced(text.trim(), 250);
  const canSearch = can("analytics:read");

  useEffect(() => { if (paletteOpen) { setText(""); setActive(0); setTimeout(() => input.current?.focus(), 0); } }, [paletteOpen]);

  const found = useQuery({ queryKey: ["search", term], queryFn: () => searchApi.query(term), enabled: paletteOpen && canSearch && term.length >= 2, staleTime: 15_000 });

  const items = useMemo<Item[]>(() => {
    const close = () => setPalette(false);
    const go = (to: string) => () => { close(); navigate(to); };
    const q = text.trim().toLowerCase();
    const match = (s: string) => !q || s.toLowerCase().includes(q);
    const pages: Item[] = NAV.filter((n) => (!n.permission || can(n.permission)) && match(n.label)).map((n) => ({ id: `page:${n.to}`, group: "Pages", label: n.label, icon: n.icon, run: go(n.to) }));
    const actions: Item[] = [
      { id: "act:theme", group: "Commands", label: "Toggle light / dark theme", icon: Moon, run: () => { close(); toggleTheme(); } },
      { id: "act:keys", group: "Commands", label: "Show keyboard shortcuts", icon: Keyboard, run: () => setHelp(true) },
      { id: "act:out", group: "Commands", label: "Sign out", icon: LogOut, run: async () => { close(); await logout(); navigate("/"); } },
    ].filter((a) => match(a.label));
    const hits: Item[] = (term === text.trim() ? found.data?.results ?? [] : []).map((h) => ({ id: `hit:${h.type}:${h.id}`, group: "Records", label: h.title, hint: h.subtitle ?? undefined, icon: HIT_ICON[h.type], run: go(h.url) }));
    return [...hits, ...pages, ...actions];
  }, [text, term, found.data, can, navigate, setPalette, setHelp, toggleTheme, logout]);

  useEffect(() => { setActive(0); }, [text, found.data]);
  useEffect(() => { list.current?.querySelector<HTMLElement>(`[data-index="${active}"]`)?.scrollIntoView({ block: "nearest" }); }, [active]);

  const onKey = (e: ReactKeyboardEvent) => {
    if (e.key === "Escape") { e.preventDefault(); setPalette(false); }
    else if (e.key === "ArrowDown") { e.preventDefault(); setActive((i) => (items.length ? (i + 1) % items.length : 0)); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setActive((i) => (items.length ? (i - 1 + items.length) % items.length : 0)); }
    else if (e.key === "Home") { e.preventDefault(); setActive(0); }
    else if (e.key === "End") { e.preventDefault(); setActive(Math.max(items.length - 1, 0)); }
    else if (e.key === "Enter") { e.preventDefault(); items[active]?.run(); }
  };

  const searching = canSearch && term.length >= 2 && (found.isFetching || term !== text.trim());
  let lastGroup = "";
  const rows: ReactNode[] = [];
  items.forEach((it, i) => {
    if (it.group !== lastGroup) { lastGroup = it.group; rows.push(<li key={`g-${it.group}`} role="presentation" className="px-3 pb-1 pt-3 text-xs font-semibold uppercase tracking-wide text-muted">{it.group}</li>); }
    rows.push(
      <li key={it.id} id={`cmd-${i}`} data-index={i} role="option" aria-selected={i === active}>
        <button type="button" tabIndex={-1} onMouseMove={() => setActive(i)} onClick={() => it.run()}
          className={cn("flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-sm", i === active ? "bg-electric/20 text-ink" : "text-ink/90")}>
          <it.icon size={16} className="shrink-0 text-muted" />
          <span className="min-w-0 flex-1 truncate">{it.label}{it.hint && <span className="ml-2 text-xs text-muted">{it.hint}</span>}</span>
          {i === active && <CornerDownLeft size={14} className="shrink-0 text-muted" />}
        </button>
      </li>,
    );
  });

  return (
    <AnimatePresence>
      {paletteOpen && (
        <motion.div className="fixed inset-0 z-50 flex items-start justify-center bg-black/60 p-4 pt-[12vh] backdrop-blur-sm" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onMouseDown={() => setPalette(false)}>
          <motion.div role="dialog" aria-modal="true" aria-label="Command palette" className="glass w-full max-w-xl overflow-hidden rounded-2xl" initial={{ scale: 0.97, y: -8 }} animate={{ scale: 1, y: 0 }} exit={{ scale: 0.98, opacity: 0 }} onMouseDown={(e) => e.stopPropagation()} onKeyDown={onKey}>
            <div className="flex items-center gap-3 border-b border-line px-4 py-3">
              <Search size={18} className="text-muted" />
              <input ref={input} value={text} onChange={(e) => setText(e.target.value)} placeholder={canSearch ? "Search vehicles, drivers, deliveries, or jump to a page…" : "Jump to a page…"}
                role="combobox" aria-expanded="true" aria-controls="cmd-list" aria-activedescendant={items.length ? `cmd-${active}` : undefined} aria-label="Search or run a command"
                className="w-full bg-transparent text-ink outline-none placeholder:text-muted/70" />
              <kbd className="rounded-md border border-line px-1.5 py-0.5 font-mono text-xs text-muted">Esc</kbd>
            </div>
            <ul id="cmd-list" ref={list} role="listbox" aria-label="Results" className="max-h-[50vh] overflow-y-auto p-2 pb-3">
              {rows}
              {items.length === 0 && <li className="px-3 py-6 text-center text-sm text-muted">{searching ? "Searching…" : "Nothing found."}</li>}
              {items.length > 0 && searching && <li className="px-3 pt-2 text-xs text-muted">Searching records…</li>}
              {found.isError && <li className="px-3 pt-2 text-xs text-danger" role="alert">Search failed: {found.error.message}</li>}
            </ul>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
