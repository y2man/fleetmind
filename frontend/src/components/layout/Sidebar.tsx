import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { useEffect, useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { LogOut, PanelLeftClose, PanelLeftOpen, X } from "lucide-react";
import { useAuth } from "@/store/auth";
import { NAV } from "@/config/nav";
import { cn } from "@/utils/cn";

interface Props {
  mobileOpen: boolean;
  onMobileClose: () => void;
}

export function Sidebar({ mobileOpen, onMobileClose }: Props) {
  const [collapsed, setCollapsed] = useState(() => window.innerWidth < 1024);
  const [expandedWidth, setExpandedWidth] = useState(232);
  const [isResizing, setIsResizing] = useState(false);
  const reduceMotion = useReducedMotion();
  const { user, can, logout } = useAuth();
  const nav = useNavigate();
  const isCollapsed = mobileOpen ? false : collapsed;
  const resizeBy = (delta: number) => setExpandedWidth((width) => Math.min(360, Math.max(200, width + delta)));

  useEffect(() => {
    const breakpoint = window.matchMedia("(max-width: 1023px)");
    const update = () => setCollapsed(breakpoint.matches);
    breakpoint.addEventListener("change", update);
    return () => breakpoint.removeEventListener("change", update);
  }, []);

  return (
    <>
      <AnimatePresence>
        {mobileOpen && (
          <motion.button
            type="button"
            aria-label="Close navigation menu"
            initial={reduceMotion ? false : { opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={reduceMotion ? undefined : { opacity: 0 }}
            onClick={onMobileClose}
            className="fixed inset-0 z-40 bg-black/55 backdrop-blur-sm md:hidden"
          />
        )}
      </AnimatePresence>
      <motion.aside
        id="app-sidebar"
        animate={{ width: mobileOpen ? 232 : collapsed ? 72 : expandedWidth }}
        initial={false}
        transition={isResizing || reduceMotion ? { duration: 0 } : { type: "spring", stiffness: 260, damping: 30 }}
        className={cn(
          "glass relative z-50 h-screen min-h-0 shrink-0 flex-col gap-1 overflow-hidden border-y-0 border-l-0 p-3",
          isResizing && "select-none",
          mobileOpen ? "fixed inset-y-0 left-0 flex w-[232px] shadow-2xl md:sticky md:top-0" : "hidden md:sticky md:top-0 md:flex",
        )}
      >
      <div className="mb-4 flex shrink-0 items-center justify-between px-2 pt-1">
        <div className="flex min-w-0 items-center gap-2">
          <img src="/logo-mark.svg" alt="" className="h-8 w-8 shrink-0" />
          <AnimatePresence initial={false}>
            {!isCollapsed && (
              <motion.span
                initial={reduceMotion ? false : { opacity: 0, x: -12, filter: "blur(5px)" }}
                animate={{ opacity: 1, x: 0, filter: "blur(0px)" }}
                exit={reduceMotion ? undefined : { opacity: 0, x: -12, filter: "blur(5px)" }}
                transition={{ duration: reduceMotion ? 0 : 0.24 }}
                className="text-gradient text-xl font-extrabold"
              >
                FleetMind
              </motion.span>
            )}
          </AnimatePresence>
        </div>
        <motion.button
          onClick={mobileOpen ? onMobileClose : () => setCollapsed((c) => !c)}
          aria-label={mobileOpen ? "Close navigation menu" : collapsed ? "Expand sidebar" : "Collapse sidebar"}
          whileHover={reduceMotion ? undefined : { rotate: mobileOpen || collapsed ? 5 : -5, scale: 1.08 }}
          whileTap={reduceMotion ? undefined : { scale: 0.9 }}
          className="focus-ring rounded-lg p-1 text-muted hover:text-ink"
        >
          {mobileOpen ? <X size={20} /> : collapsed ? <PanelLeftOpen size={20} /> : <PanelLeftClose size={20} />}
        </motion.button>
      </div>
      <nav aria-label="Main navigation" tabIndex={0} className="sidebar-nav flex min-h-0 flex-1 flex-col gap-1 overflow-x-hidden overflow-y-auto overscroll-contain">
      {NAV.filter((n) => !n.permission || can(n.permission)).map(({ to, label, icon: Icon }, index) => (
        <motion.div
          key={to}
          initial={reduceMotion ? false : "hidden"}
          animate="rest"
          transition={{ delay: reduceMotion ? 0 : index * 0.05, duration: reduceMotion ? 0 : 0.32, type: "spring", stiffness: 360, damping: 24 }}
          whileHover={reduceMotion ? undefined : "hover"}
          whileTap={reduceMotion ? undefined : "tap"}
          variants={{
            hidden: { opacity: 0, x: -14 },
            rest: { opacity: 1, x: 0, scale: 1 },
            hover: { opacity: 1, x: 6, scale: 1.035 },
            tap: { opacity: 1, scale: 0.94 },
          }}
          className="group shrink-0"
        >
          <NavLink to={to} end title={label} onClick={onMobileClose}
            className={({ isActive }) => cn("focus-ring relative flex items-center gap-3 overflow-hidden rounded-xl px-3 py-2.5 text-sm transition-colors", isActive ? "text-ink" : "text-muted hover:text-ink")}>
            {({ isActive }) => (
              <>
                {isActive && (
                  <motion.span
                    layoutId="sidebar-active-indicator"
                    transition={{ type: "spring", stiffness: 380, damping: 28 }}
                    className="absolute inset-0 rounded-xl border border-electric/25 bg-gradient-to-r from-electric/25 via-electric/10 to-violet/25 shadow-glow"
                  />
                )}
                <span className={cn("absolute inset-0 rounded-xl bg-gradient-to-r from-electric/10 to-violet/15 opacity-0 transition-opacity duration-200 group-hover:opacity-100", isActive && "hidden")} />
                <motion.span
                  variants={{ rest: { rotate: 0, scale: 1 }, hover: { rotate: -10, scale: 1.18 } }}
                  transition={{ type: "spring", stiffness: 450, damping: 12 }}
                  className="relative z-10 shrink-0"
                >
                  <Icon size={18} />
                </motion.span>
                <AnimatePresence initial={false}>
                  {!isCollapsed && (
                    <motion.span
                      initial={reduceMotion ? false : { opacity: 0, x: -10, filter: "blur(4px)" }}
                      animate={{ opacity: 1, x: 0, filter: "blur(0px)" }}
                      exit={reduceMotion ? undefined : { opacity: 0, x: -10, filter: "blur(4px)" }}
                      transition={{ duration: reduceMotion ? 0 : 0.18 }}
                      className="relative z-10 whitespace-nowrap"
                    >
                      {label}
                    </motion.span>
                  )}
                </AnimatePresence>
              </>
            )}
          </NavLink>
        </motion.div>
      ))}
      </nav>
      <div className="shrink-0 border-t border-line pt-2">
        <motion.button
          onClick={async () => { onMobileClose(); await logout(); nav("/"); }}
          title="Sign out"
          whileHover={reduceMotion ? undefined : { x: 4 }}
          whileTap={reduceMotion ? undefined : { scale: 0.97 }}
          className="focus-ring flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm text-muted hover:bg-surface/70 hover:text-ink"
        >
          <LogOut size={18} className="shrink-0" />
          {!isCollapsed && <span className="truncate">Sign out{user ? ` · ${user.full_name}` : ""}</span>}
        </motion.button>
      </div>
      {!collapsed && !mobileOpen && (
        <motion.div
          role="separator"
          aria-label="Resize sidebar"
          aria-orientation="vertical"
          aria-valuemin={200}
          aria-valuemax={360}
          aria-valuenow={expandedWidth}
          aria-valuetext={`${expandedWidth} pixels`}
          tabIndex={0}
          onPointerDown={(event) => {
            event.preventDefault();
            event.currentTarget.setPointerCapture(event.pointerId);
            setIsResizing(true);
          }}
          onPointerMove={(event) => {
            if (isResizing) setExpandedWidth(Math.min(360, Math.max(200, event.clientX)));
          }}
          onPointerUp={() => setIsResizing(false)}
          onPointerCancel={() => setIsResizing(false)}
          onLostPointerCapture={() => setIsResizing(false)}
          onKeyDown={(event) => {
            if (event.key === "ArrowLeft") {
              event.preventDefault();
              resizeBy(-12);
            } else if (event.key === "ArrowRight") {
              event.preventDefault();
              resizeBy(12);
            }
          }}
          whileHover={reduceMotion ? undefined : { opacity: 1, scaleX: 1.5 }}
          className={cn(
            "absolute inset-y-0 right-0 z-[60] w-1 cursor-col-resize touch-none bg-gradient-to-b from-electric/0 via-electric/50 to-violet/0 opacity-0 transition-opacity hover:opacity-100 focus-visible:opacity-100",
            isResizing && "opacity-100",
          )}
        />
      )}
      </motion.aside>
    </>
  );
}
