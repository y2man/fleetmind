import { AnimatePresence, motion } from "framer-motion";
import { useState } from "react";
import { Link } from "react-router-dom";
import { ChevronDown, Check } from "lucide-react";
import { AnimatedNumber } from "@/components/animations/AnimatedNumber";
import { Badge, Button, GlassCard } from "@/components/ui";
import { FAQ, FEATURES, PLANS, STATS, STEPS, TESTIMONIALS } from "./content";

const Title = ({ id, children, sub }: { id?: string; children: string; sub?: string }) => (
  <div id={id} data-reveal className="mb-8 scroll-mt-24 text-center"><h2 className="text-3xl font-bold">{children}</h2>{sub && <p className="mt-2 text-muted">{sub}</p>}</div>
);

export function Features() {
  return (
    <section className="mx-auto max-w-6xl px-4 py-12">
      <Title id="features" sub="Everything a logistics team needs.">Platform features</Title>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {FEATURES.map(([t, d]) => <GlassCard key={t}><h3 className="font-semibold">{t}</h3><p className="mt-2 text-sm text-muted">{d}</p></GlassCard>)}
      </div>
    </section>
  );
}
export function HowItWorks() {
  return (
    <section className="mx-auto max-w-6xl px-4 py-12">
      <Title id="how">How it works</Title>
      <div className="grid gap-4 md:grid-cols-4">
        {STEPS.map(([t, d], i) => <GlassCard key={t}><span className="text-gradient text-3xl font-extrabold">{i + 1}</span><h3 className="mt-2 font-semibold">{t}</h3><p className="mt-1 text-sm text-muted">{d}</p></GlassCard>)}
      </div>
    </section>
  );
}
export function StatsAndTestimonials() {
  return (
    <section className="mx-auto max-w-6xl px-4 py-12">
      <div className="mb-2 text-center"><Badge tone="warn">Demo figures</Badge></div>
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {STATS.map((s) => <GlassCard key={s.label} className="text-center"><p className="text-gradient text-4xl font-extrabold"><AnimatedNumber value={s.value} suffix={s.suffix} /></p><p className="mt-1 text-sm text-muted">{s.label}</p></GlassCard>)}
      </div>
      <div className="mt-8 grid gap-4 md:grid-cols-3">
        {TESTIMONIALS.map(([q, who]) => <GlassCard key={q}><p>{q}</p><p className="mt-3 text-xs text-muted">{who} (demo content)</p></GlassCard>)}
      </div>
    </section>
  );
}
export function Pricing() {
  return (
    <section className="mx-auto max-w-6xl px-4 py-12">
      <Title id="pricing" sub="Demo pricing for illustration.">Pricing</Title>
      <div className="grid gap-4 md:grid-cols-3">
        {PLANS.map((p) => (
          <GlassCard key={p.name} className={"hot" in p ? "border-electric shadow-glow" : ""}>
            <h3 className="font-semibold">{p.name}</h3><p className="mt-2 text-3xl font-extrabold">{p.price}</p><p className="text-xs text-muted">{p.note}</p>
            <ul className="my-4 space-y-2 text-sm">{p.items.map((i) => <li key={i} className="flex gap-2"><Check size={16} className="text-ok" />{i}</li>)}</ul>
            <Link to="/signup"><Button variant={"hot" in p ? "primary" : "outline"} className="w-full">Get started</Button></Link>
          </GlassCard>
        ))}
      </div>
    </section>
  );
}
export function Faq() {
  const [open, setOpen] = useState<number | null>(0);
  return (
    <section className="mx-auto max-w-3xl px-4 py-12">
      <Title id="faq">FAQ</Title>
      <div className="space-y-3">
        {FAQ.map(([q, a], i) => (
          <div key={q} className="glass rounded-xl">
            <button onClick={() => setOpen(open === i ? null : i)} aria-expanded={open === i} className="focus-ring flex w-full items-center justify-between rounded-xl px-4 py-3 text-left font-medium">
              {q}<ChevronDown size={18} className={open === i ? "rotate-180 transition" : "transition"} />
            </button>
            <AnimatePresence initial={false}>
              {open === i && <motion.p initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="overflow-hidden px-4 pb-3 text-sm text-muted">{a}</motion.p>}
            </AnimatePresence>
          </div>
        ))}
      </div>
    </section>
  );
}
export function Footer() {
  return (
    <footer className="border-t border-line py-8 text-center text-sm text-muted">
      <p><span className="text-gradient font-bold">FleetMind</span> · © 2026 · Demo product</p>
      <p className="mt-1"><a href="#top" className="hover:text-ink">Back to top</a> · <Link to="/status" className="hover:text-ink">System status</Link></p>
    </footer>
  );
}
