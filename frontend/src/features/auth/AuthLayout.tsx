import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { Activity, ArrowLeft, ArrowUpRight, Check, MapPin, Route, Truck } from "lucide-react";
import type { ReactNode } from "react";
import { Link, useLocation } from "react-router-dom";
import { ParticleBackground } from "@/components/animations/ParticleBackground";
import { ThemeToggle } from "@/components/layout/ThemeToggle";

const routePath = "M28 122 C92 122 115 56 190 66 S290 146 360 120 S445 45 515 58 S575 105 622 100";

export function AuthLayout({ title, subtitle, children }: { title: string; subtitle?: string; children: ReactNode }) {
  const reduceMotion = useReducedMotion();
  const { pathname } = useLocation();
  const signingUp = pathname === "/signup";

  return (
    <main className="relative min-h-screen overflow-hidden">
      <ParticleBackground count={28} />
      <div className="relative mx-auto grid min-h-screen max-w-[1600px] lg:grid-cols-[1.08fr_0.92fr]">
        <motion.aside
          initial={reduceMotion ? false : { opacity: 0, x: -28 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: reduceMotion ? 0 : 0.65, ease: [0.22, 1, 0.36, 1] }}
          className="relative flex min-h-[20rem] flex-col overflow-hidden border-b border-line/70 px-6 py-6 sm:min-h-[24rem] sm:px-10 lg:sticky lg:top-0 lg:h-screen lg:border-b-0 lg:border-r lg:px-12 lg:py-9 xl:px-16"
        >
          <div className="pointer-events-none absolute -left-24 top-1/4 h-80 w-80 rounded-full bg-electric/10 blur-[100px]" />
          <div className="pointer-events-none absolute -right-20 bottom-0 h-72 w-72 rounded-full bg-violet/10 blur-[100px]" />
          <Link to="/" className="relative z-10 inline-flex w-fit items-center gap-2 text-xl font-extrabold tracking-tight text-ink">
            <img src="/logo-mark.svg" alt="" className="h-9 w-9" />
            <span>FleetMind</span>
          </Link>

          <div className="relative z-10 my-auto max-w-xl py-9 lg:py-12">
            <motion.p
              initial={reduceMotion ? false : { opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: reduceMotion ? 0 : 0.12, duration: 0.5 }}
              className="mb-4 inline-flex items-center gap-2 rounded-full border border-electric/25 bg-electric/10 px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.18em] text-electric"
            >
              <Activity size={13} /> Fleet operations, connected
            </motion.p>
            <motion.h2
              initial={reduceMotion ? false : { opacity: 0, y: 18 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: reduceMotion ? 0 : 0.2, duration: 0.6 }}
              className="max-w-lg text-4xl font-extrabold leading-[1.06] tracking-tight sm:text-5xl xl:text-6xl"
            >
              Every mile.
              <span className="mt-1 block">Every delivery.</span>
              <span className="mt-1 block text-gradient">In view.</span>
            </motion.h2>
            <motion.p
              initial={reduceMotion ? false : { opacity: 0, y: 14 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: reduceMotion ? 0 : 0.3, duration: 0.55 }}
              className="mt-5 max-w-md text-sm leading-7 text-muted sm:text-base"
            >
              One practical workspace for the people, vehicles and deliveries that keep your operation moving.
            </motion.p>

            <div className="relative mt-8 h-36 max-w-2xl overflow-hidden rounded-2xl border border-line/80 bg-surface/50 p-3 sm:mt-10 sm:h-44 sm:p-5">
              <div className="absolute inset-0 opacity-30 [background-image:linear-gradient(rgb(110_130_180/0.15)_1px,transparent_1px),linear-gradient(90deg,rgb(110_130_180/0.15)_1px,transparent_1px)] [background-size:28px_28px]" />
              <svg viewBox="0 0 650 170" className="absolute inset-0 h-full w-full" aria-hidden="true">
                <path d={routePath} fill="none" stroke="rgb(116 132 170 / 0.22)" strokeWidth="13" strokeLinecap="round" />
                <motion.path
                  d={routePath}
                  fill="none"
                  stroke="url(#auth-route-gradient)"
                  strokeWidth="3"
                  strokeLinecap="round"
                  initial={reduceMotion ? false : { pathLength: 0, opacity: 0.4 }}
                  animate={{ pathLength: 1, opacity: 1 }}
                  transition={{ duration: reduceMotion ? 0 : 2.2, delay: reduceMotion ? 0 : 0.35, ease: "easeInOut" }}
                />
                <defs>
                  <linearGradient id="auth-route-gradient" x1="0" x2="1">
                    <stop stopColor="#4d8dff" />
                    <stop offset="1" stopColor="#9b6bff" />
                  </linearGradient>
                </defs>
                {[28, 190, 360, 515, 622].map((x, index) => (
                  <circle key={x} cx={x} cy={[122, 66, 120, 58, 100][index]} r="5" fill={index === 4 ? "#2fe0a0" : "#7ba8ff"} />
                ))}
                <motion.circle
                  r="7"
                  fill="#fff"
                  stroke="#4d8dff"
                  strokeWidth="4"
                  initial={reduceMotion ? false : { cx: 28, cy: 122 }}
                  animate={{ cx: [28, 190, 360, 515, 622], cy: [122, 66, 120, 58, 100] }}
                  transition={{ duration: reduceMotion ? 0 : 7, repeat: reduceMotion ? 0 : Infinity, ease: "easeInOut", delay: 0.4 }}
                />
              </svg>
              <motion.div
                initial={reduceMotion ? false : { opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: reduceMotion ? 0 : 0.7, duration: 0.4 }}
                className="absolute bottom-3 left-3 inline-flex items-center gap-2 rounded-xl border border-line bg-bg/90 px-3 py-2 text-[11px] shadow-lg backdrop-blur sm:bottom-4 sm:left-4"
              >
                <span className="grid h-7 w-7 place-items-center rounded-lg bg-electric/15 text-electric"><Truck size={15} /></span>
                <span><span className="block font-semibold text-ink">Route in motion</span><span className="text-muted">From dispatch to delivery</span></span>
              </motion.div>
              <div className="absolute right-3 top-3 flex items-center gap-1.5 text-[9px] uppercase tracking-[0.16em] text-muted sm:right-4 sm:top-4">
                <MapPin size={11} /> Planned route
              </div>
            </div>

            <div className="mt-5 hidden grid-cols-3 gap-3 sm:grid">
              {[
                { icon: Truck, label: "Fleet" },
                { icon: Route, label: "Routes" },
                { icon: Check, label: "Deliveries" },
              ].map(({ icon: FeatureIcon, label }) => (
                <div key={label} className="flex items-center gap-2 text-xs text-muted">
                  <FeatureIcon size={14} className="text-electric" /> {label}
                </div>
              ))}
            </div>
          </div>

          <p className="relative z-10 hidden text-xs text-muted lg:block">FleetMind · A clearer view of daily operations</p>
        </motion.aside>

        <section className="relative flex min-h-[70vh] items-center justify-center px-5 py-10 sm:px-10 lg:min-h-screen lg:px-12 xl:px-16">
          <div className="pointer-events-none absolute right-8 top-12 h-52 w-52 rounded-full bg-electric/[0.06] blur-[80px]" />
          <div className="relative z-10 w-full max-w-[440px]">
            <div className="mb-10 flex items-center justify-between">
              <Link to="/" className="inline-flex items-center gap-2 text-xs font-medium text-muted transition-colors hover:text-ink">
                <ArrowLeft size={14} /> Back to home
              </Link>
              <ThemeToggle />
            </div>
            <AnimatePresence mode="wait" initial={false}>
              <motion.div
                key={pathname}
                initial={reduceMotion ? false : { opacity: 0, y: 16, filter: "blur(4px)" }}
                animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
                exit={reduceMotion ? undefined : { opacity: 0, y: -8, filter: "blur(3px)" }}
                transition={{ duration: reduceMotion ? 0 : 0.38, ease: [0.22, 1, 0.36, 1] }}
              >
                <p className="mb-3 text-[11px] font-semibold uppercase tracking-[0.2em] text-electric">
                  {signingUp ? "Start your workspace" : "Workspace access"}
                </p>
                <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">{title}</h1>
                {subtitle && <p className="mt-2 text-sm leading-6 text-muted">{subtitle}</p>}
                <div className="mt-7 space-y-5">{children}</div>
              </motion.div>
            </AnimatePresence>
            <div className="mt-8 flex items-center gap-2 border-t border-line/70 pt-5 text-[11px] text-muted">
              <span className="grid h-6 w-6 place-items-center rounded-full border border-ok/30 bg-ok/10 text-ok"><Check size={12} /></span>
              Your workspace is separated from other organizations.
              <ArrowUpRight size={12} className="ml-auto shrink-0 opacity-50" />
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}

export function FormError({ message }: { message?: string }) {
  return message ? <p role="alert" className="rounded-lg border border-danger/40 bg-danger/10 px-3 py-2 text-sm text-danger">{message}</p> : null;
}

export function DevLink({ link }: { link?: string | null }) {
  if (!link) return null;
  return (
    <p className="rounded-lg border border-warn/40 bg-warn/10 px-3 py-2 text-sm text-warn">
      Development mode: email isn’t sent. <a className="underline" href={link}>Open the link from the email</a>
    </p>
  );
}
