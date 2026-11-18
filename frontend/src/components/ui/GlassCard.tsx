import { motion, useReducedMotion } from "framer-motion";
import type { ReactNode } from "react";
import { cn } from "@/utils/cn";

export function GlassCard({ children, className, hover = true, ...rest }: { children: ReactNode; className?: string; hover?: boolean; "data-reveal"?: boolean }) {
  const reduceMotion = useReducedMotion();
  return (
    <motion.div
      initial={reduceMotion ? false : { opacity: 0, y: 34, scale: 0.96 }}
      whileInView={reduceMotion ? undefined : { opacity: 1, y: 0, scale: 1 }}
      viewport={{ once: true, amount: 0.12, margin: "0px 0px -32px 0px" }}
      whileHover={!reduceMotion && hover ? { y: -7, scale: 1.015 } : undefined}
      transition={{ duration: 0.68, ease: [0.22, 1, 0.36, 1] }}
      {...rest}
      className={cn("glass rounded-2xl p-5 transition-[border-color,box-shadow] duration-300", hover && "hover:border-electric/50 hover:shadow-glow", className)}
    >
      {children}
    </motion.div>
  );
}
