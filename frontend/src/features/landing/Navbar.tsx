import { useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { Menu, X } from "lucide-react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui";
import { ThemeToggle } from "@/components/layout/ThemeToggle";

const links = [["Features", "#features"], ["How it works", "#how"], ["Pricing", "#pricing"], ["FAQ", "#faq"]];
const navItemVariants = {
  rest: { y: 0, scale: 1 },
  hover: { y: -3, scale: 1.06 },
  tap: { scale: 0.96 },
};
const navSurfaceVariants = {
  rest: { opacity: 0, scale: 0.82 },
  hover: { opacity: 1, scale: 1 },
  tap: { opacity: 0.85, scale: 0.96 },
};
export function Navbar() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const reduceMotion = useReducedMotion();

  return (
    <motion.header
      initial={reduceMotion ? false : { y: -24, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: reduceMotion ? 0 : 0.55, ease: "easeOut" }}
      className="glass sticky top-0 z-40 border-x-0 border-t-0"
    >
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3">
        <motion.a
          href="#top"
          whileHover={reduceMotion ? undefined : { scale: 1.08 }}
          whileTap={reduceMotion ? undefined : { scale: 0.94 }}
          className="flex items-center gap-2 text-gradient text-xl font-extrabold"
        >
          <motion.img
            src="/logo-mark.svg"
            alt=""
            className="h-8 w-8"
            whileHover={reduceMotion ? undefined : { rotate: 12, scale: 1.18 }}
            transition={{ type: "spring", stiffness: 420, damping: 12 }}
          />
          FleetMind
        </motion.a>
        <nav className="hidden items-center gap-2 text-sm text-muted md:flex">
          {links.map(([label, href], index) => (
            <motion.a
              key={href}
              href={href}
              initial={reduceMotion ? false : "hidden"}
              animate="rest"
              transition={{ delay: reduceMotion ? 0 : 0.12 + index * 0.07 }}
              whileHover={reduceMotion ? undefined : "hover"}
              whileTap={reduceMotion ? undefined : "tap"}
              variants={{
                hidden: { opacity: 0, y: -8 },
                rest: { ...navItemVariants.rest, opacity: 1 },
                hover: { ...navItemVariants.hover, opacity: 1 },
                tap: { ...navItemVariants.tap, opacity: 1 },
              }}
              className="group relative isolate rounded-xl px-3 py-2 transition-colors hover:text-ink"
            >
              <motion.span
                variants={navSurfaceVariants}
                transition={{ duration: reduceMotion ? 0 : 0.22, ease: "easeOut" }}
                className="absolute inset-0 -z-10 rounded-xl bg-gradient-to-br from-electric/20 via-surface/70 to-violet/20 shadow-glow"
              />
              <span>{label}</span>
              <motion.span
                variants={{ rest: { scaleX: 0 }, hover: { scaleX: 1 }, tap: { scaleX: 0.6 } }}
                transition={{ duration: reduceMotion ? 0 : 0.22 }}
                className="absolute inset-x-3 bottom-1 h-0.5 origin-left rounded-full bg-gradient-to-r from-electric to-violet"
              />
            </motion.a>
          ))}
        </nav>
        <div className="flex items-center gap-2">
          <ThemeToggle />
          <Link to="/signin"><Button size="sm" variant="ghost">Sign in</Button></Link>
          <Link to="/signup" className="hidden sm:inline-flex"><Button size="sm">Get started</Button></Link>
          <button
            type="button"
            className="focus-ring rounded-xl p-2 text-muted transition-colors hover:bg-surface/70 hover:text-ink md:hidden"
            aria-label={mobileOpen ? "Close navigation menu" : "Open navigation menu"}
            aria-expanded={mobileOpen}
            aria-controls="mobile-navigation"
            onClick={() => setMobileOpen((open) => !open)}
          >
            <motion.span animate={{ rotate: mobileOpen ? 90 : 0 }} transition={{ duration: reduceMotion ? 0 : 0.2 }} className="block">
              {mobileOpen ? <X size={20} /> : <Menu size={20} />}
            </motion.span>
          </button>
        </div>
      </div>
      <AnimatePresence initial={false}>
        {mobileOpen && (
          <motion.nav
            id="mobile-navigation"
            initial={reduceMotion ? false : { height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={reduceMotion ? undefined : { height: 0, opacity: 0 }}
            transition={{ duration: reduceMotion ? 0 : 0.24, ease: "easeOut" }}
            className="overflow-hidden border-t border-line md:hidden"
          >
            <div className="mx-auto flex max-w-6xl flex-col gap-1 px-4 py-3">
              {links.map(([label, href], index) => (
                <motion.a
                  key={href}
                  href={href}
                  onClick={() => setMobileOpen(false)}
                  initial={reduceMotion ? false : { opacity: 0, x: -12 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: reduceMotion ? 0 : index * 0.045 }}
                  whileTap={reduceMotion ? undefined : { scale: 0.98 }}
                  whileHover={reduceMotion ? undefined : { x: 8, scale: 1.015 }}
                  className="rounded-xl border border-transparent px-3 py-2.5 text-sm text-muted transition-colors hover:border-electric/20 hover:bg-gradient-to-r hover:from-electric/15 hover:to-violet/15 hover:text-ink"
                >
                  {label}
                </motion.a>
              ))}
              <Link to="/signup" onClick={() => setMobileOpen(false)} className="mt-1 sm:hidden">
                <Button className="w-full" size="sm">Get started</Button>
              </Link>
            </div>
          </motion.nav>
        )}
      </AnimatePresence>
    </motion.header>
  );
}
