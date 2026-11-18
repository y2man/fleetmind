import { motion, type HTMLMotionProps } from "framer-motion";
import { cn } from "@/utils/cn";

type Variant = "primary" | "outline" | "ghost" | "danger";
interface Props extends HTMLMotionProps<"button"> { variant?: Variant; size?: "sm" | "md" }

const styles: Record<Variant, string> = {
  primary: "bg-gradient-to-r from-electric to-violet text-white hover:shadow-glow",
  outline: "border border-line text-ink hover:border-electric hover:shadow-glow",
  ghost: "text-muted hover:text-ink hover:bg-surface/70",
  danger: "bg-danger text-white hover:opacity-90",
};

export function Button({ variant = "primary", size = "md", className, ...rest }: Props) {
  return (
    <motion.button
      whileHover={{ scale: 1.03 }}
      whileTap={{ scale: 0.97 }}
      className={cn("focus-ring inline-flex items-center justify-center gap-2 rounded-xl font-medium transition-shadow disabled:opacity-50", size === "sm" ? "px-3 py-1.5 text-sm" : "px-4 py-2", styles[variant], className)}
      {...rest}
    />
  );
}
