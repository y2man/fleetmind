import { lazy, Suspense, useLayoutEffect, useRef } from "react";
import { Link } from "react-router-dom";
import { motion, useReducedMotion } from "framer-motion";
import gsap from "gsap";
import { Activity, ArrowDown, ArrowRight, Route, Sparkles, Truck, Users } from "lucide-react";
import { Badge, Button } from "@/components/ui";

const Hero3D = lazy(() => import("./Hero3D"));

export function Hero() {
  const root = useRef<HTMLElement>(null);
  const reduce = useReducedMotion();
  useLayoutEffect(() => {
    if (reduce) return;
    const ctx = gsap.context(() => { gsap.from("[data-hero]", { y: 40, opacity: 0, stagger: 0.12, duration: 0.9, ease: "power3.out" }); }, root);
    return () => ctx.revert();
  }, [reduce]);
  return (
    <section ref={root} id="top" className="relative mx-auto grid min-h-[calc(100svh-4rem)] max-w-6xl items-center gap-5 overflow-hidden px-4 py-12 md:grid-cols-2 md:gap-0 md:py-8">
      <div className="relative z-10 py-8 md:py-12">
        <div data-hero className="mb-5 inline-flex items-center gap-2 rounded-full border border-electric/25 bg-electric/10 px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.18em] text-electric">
          <Sparkles size={14} /> AI-powered fleet platform
        </div>
        <h1 data-hero className="max-w-2xl text-5xl font-extrabold leading-[1.04] tracking-tight sm:text-6xl lg:text-7xl">
          Move smarter.
          <span className="mt-1 block">Deliver faster.</span>
          <span className="mt-1 block text-gradient">Think ahead.</span>
        </h1>
        <p data-hero className="mt-6 max-w-lg text-base leading-7 text-muted md:text-lg">
          Bring vehicles, drivers, deliveries and routes into one clear command center—and keep every operation moving.
        </p>
        <div data-hero className="mt-8 flex flex-wrap gap-3">
          <Link to="/signup"><Button className="group min-h-12 px-5">Create your account <ArrowRight size={17} className="transition-transform group-hover:translate-x-1" /></Button></Link>
          <a href="#features"><Button variant="outline" className="min-h-12 px-5">Explore the platform</Button></a>
        </div>
        <div data-hero className="mt-8 flex flex-wrap items-center gap-x-5 gap-y-2 text-xs text-muted">
          <span className="inline-flex items-center gap-2"><span className="h-1.5 w-1.5 rounded-full bg-ok shadow-[0_0_12px_rgb(var(--ok)/0.8)]" />One connected workspace</span>
          <span>Fleet · Routes · Deliveries</span>
        </div>
        <a href="#showcase" className="mt-12 hidden items-center gap-2 text-xs font-medium text-muted transition-colors hover:text-ink md:inline-flex">
          Scroll to explore <ArrowDown size={14} />
        </a>
      </div>
      <div data-hero data-hero-visual className="relative mx-auto grid h-[22rem] w-full max-w-[34rem] place-items-center md:h-[34rem]" aria-hidden="true">
        <div className="absolute inset-[12%] rounded-full border border-electric/15 bg-electric/[0.03] shadow-[0_0_100px_rgb(var(--electric)/0.12)]" />
        <motion.div
          className="absolute inset-[7%] rounded-full border border-dashed border-violet/25"
          animate={reduce ? undefined : { rotate: 360 }}
          transition={{ duration: 48, repeat: Infinity, ease: "linear" }}
        />
        <motion.div
          className="absolute inset-[19%] rounded-full border border-electric/20"
          animate={reduce ? undefined : { rotate: -360 }}
          transition={{ duration: 35, repeat: Infinity, ease: "linear" }}
        />
        <div className="absolute inset-0 z-10">
          {!reduce && <Suspense fallback={null}><Hero3D /></Suspense>}
        </div>
        <motion.div
          className="glass absolute left-0 top-[22%] z-20 rounded-2xl p-3 shadow-glow sm:p-4"
          animate={reduce ? undefined : { y: [0, -9, 0] }}
          transition={{ duration: 5, repeat: Infinity, ease: "easeInOut" }}
        >
          <div className="flex items-center gap-3">
            <span className="grid h-10 w-10 place-items-center rounded-xl bg-electric/15 text-electric"><Activity size={19} /></span>
            <span><span className="block text-xs font-semibold text-ink">Fleet overview</span><span className="block text-[11px] text-muted">One connected view</span></span>
          </div>
        </motion.div>
        <motion.div
          className="glass absolute bottom-[18%] right-0 z-20 rounded-2xl p-3 shadow-glow sm:p-4"
          animate={reduce ? undefined : { y: [0, 8, 0] }}
          transition={{ duration: 4.5, repeat: Infinity, ease: "easeInOut", delay: 0.4 }}
        >
          <Badge tone="ok"><span className="mr-1.5 inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-ok" />Operations</Badge>
          <div className="mt-3 flex items-center gap-3 text-xs text-muted">
            <span className="flex items-center gap-1"><Truck size={14} className="text-electric" /> Fleet</span>
            <span className="flex items-center gap-1"><Users size={14} className="text-violet" /> Team</span>
            <span className="flex items-center gap-1"><Route size={14} className="text-ok" /> Routes</span>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
