import { useEffect, useState } from "react";
import { AnimatePresence } from "framer-motion";
import { Outlet, useLocation } from "react-router-dom";
import { Menu, Search, X } from "lucide-react";
import { Sidebar } from "./Sidebar";
import { ThemeToggle } from "./ThemeToggle";
import { PageTransition } from "./PageTransition";
import { ParticleBackground } from "@/components/animations/ParticleBackground";
import { CommandPalette } from "@/components/command/CommandPalette";
import { ShortcutsModal } from "@/components/command/ShortcutsModal";
import { NotificationBell } from "@/features/notifications/NotificationBell";
import { useAlertSweep } from "@/features/notifications/useNotifications";
import { useShortcuts } from "@/hooks/useShortcuts";
import { useUi } from "@/store/ui";

export function AppShell() {
  const { pathname } = useLocation();
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const setPalette = useUi((s) => s.setPalette);
  useShortcuts();
  useAlertSweep();
  useEffect(() => setMobileNavOpen(false), [pathname]);

  return (
    <div className="flex min-h-screen w-full min-w-0">
      <ParticleBackground />
      <Sidebar mobileOpen={mobileNavOpen} onMobileClose={() => setMobileNavOpen(false)} />
      <div className="min-w-0 flex-1">
        <header className="flex min-w-0 items-center justify-between gap-2 p-3 sm:gap-3 sm:p-4">
          <button
            onClick={() => setMobileNavOpen(true)}
            aria-label="Open navigation menu"
            aria-expanded={mobileNavOpen}
            aria-controls="app-sidebar"
            className="focus-ring glass grid h-10 w-10 shrink-0 place-items-center rounded-xl text-muted hover:text-ink md:hidden"
          >
            {mobileNavOpen ? <X size={18} /> : <Menu size={18} />}
          </button>
          <button onClick={() => setPalette(true)} aria-label="Search and commands (Ctrl or Command + K)"
            className="focus-ring glass flex min-w-0 flex-1 items-center gap-2 rounded-xl px-3 py-2 text-sm text-muted hover:shadow-glow md:max-w-xs">
            <Search size={16} aria-hidden /><span className="flex-1 truncate text-left">Search or jump to…</span>
            <kbd className="hidden rounded-md border border-line px-1.5 py-0.5 font-mono text-xs sm:inline">Ctrl K</kbd>
          </button>
          <div className="flex shrink-0 items-center gap-1 sm:gap-2"><NotificationBell /><ThemeToggle /></div>
        </header>
        <main className="min-w-0 px-3 pb-10 sm:px-4 md:px-8">
          <AnimatePresence mode="wait" initial={false}>
            <PageTransition key={pathname}><div data-app-page-root className="min-w-0"><Outlet /></div></PageTransition>
          </AnimatePresence>
        </main>
      </div>
      <CommandPalette />
      <ShortcutsModal />
    </div>
  );
}
