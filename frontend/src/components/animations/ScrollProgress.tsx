import { motion, useReducedMotion, useScroll, useSpring } from "framer-motion";

export function ScrollProgress() {
  const { scrollYProgress } = useScroll();
  const smoothProgress = useSpring(scrollYProgress, { stiffness: 120, damping: 28, mass: 0.25 });
  const reduceMotion = useReducedMotion();

  return (
    <motion.div
      aria-hidden="true"
      className="pointer-events-none fixed inset-x-0 top-0 z-[100] h-0.5 origin-left bg-gradient-to-r from-electric via-cyan-300 to-violet"
      style={{ scaleX: reduceMotion ? scrollYProgress : smoothProgress }}
    />
  );
}
