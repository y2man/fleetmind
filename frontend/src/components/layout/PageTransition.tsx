import { useLayoutEffect, useRef } from "react";
import { motion, useReducedMotion } from "framer-motion";
import type { ReactNode } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";

gsap.registerPlugin(ScrollTrigger);

export function PageTransition({ children }: { children: ReactNode }) {
  const reduceMotion = useReducedMotion();
  const root = useRef<HTMLDivElement>(null);

  useLayoutEffect(() => {
    if (reduceMotion || !root.current) return;
    const page = root.current.querySelector<HTMLElement>("[data-app-page-root] > *");
    if (!page) return;

    const sections = Array.from(page.children).filter(
      (element): element is HTMLElement =>
        element instanceof HTMLElement &&
        !element.classList.contains("glass") &&
        element.getAttribute("data-no-page-reveal") !== "true",
    );
    if (!sections.length) return;

    const context = gsap.context(() => {
      sections.forEach((section) => {
        gsap.fromTo(
          section,
          { autoAlpha: 0, y: 38, scale: 0.975 },
          {
            autoAlpha: 1,
            y: 0,
            scale: 1,
            duration: 0.72,
            ease: "power3.out",
            scrollTrigger: { trigger: section, start: "top 96%", end: "top 72%", scrub: 0.45, once: true },
          },
        );
      });
    }, root);

    return () => context.revert();
  }, [reduceMotion]);

  return (
    <motion.div
      ref={root}
      initial={reduceMotion ? false : { opacity: 0, y: 28, scale: 0.985, filter: "blur(7px)" }}
      animate={{ opacity: 1, y: 0, scale: 1, filter: "blur(0px)" }}
      exit={reduceMotion ? undefined : { opacity: 0, y: -14, scale: 0.99, filter: "blur(4px)" }}
      transition={{ duration: reduceMotion ? 0 : 0.56, ease: [0.22, 1, 0.36, 1] }}
    >
      {children}
    </motion.div>
  );
}
