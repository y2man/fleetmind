import { useLayoutEffect, useRef } from "react";
import { useReducedMotion } from "framer-motion";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { ParticleBackground } from "@/components/animations/ParticleBackground";
import { Navbar } from "./Navbar";
import { Hero } from "./Hero";
import { Showcase } from "./Showcase";
import { Faq, Features, Footer, HowItWorks, Pricing, StatsAndTestimonials } from "./Sections";

gsap.registerPlugin(ScrollTrigger);

export function LandingPage() {
  const root = useRef<HTMLDivElement>(null);
  const reduce = useReducedMotion();
  useLayoutEffect(() => {
    if (reduce) return;
    const ctx = gsap.context(() => {
      gsap.utils.toArray<HTMLElement>("[data-reveal]:not(.glass)").forEach((el) =>
        gsap.from(el, { y: 36, opacity: 0, duration: 0.8, ease: "power2.out", scrollTrigger: { trigger: el, start: "top 88%", once: true } })
      );
      gsap.to("[data-hero-visual]", {
        yPercent: 12,
        opacity: 0.7,
        ease: "none",
        scrollTrigger: { trigger: "#top", start: "top top", end: "bottom top", scrub: 1 },
      });
    }, root);
    return () => ctx.revert();
  }, [reduce]);
  return (
    <div ref={root}>
      <ParticleBackground />
      <Navbar /><Hero /><Showcase /><Features /><HowItWorks /><StatsAndTestimonials /><Pricing /><Faq /><Footer />
    </div>
  );
}
