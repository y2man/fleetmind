import { animate, useReducedMotion } from "framer-motion";
import { useEffect, useState } from "react";

export function AnimatedNumber({ value, decimals = 0, suffix = "" }: { value: number; decimals?: number; suffix?: string }) {
  const reduce = useReducedMotion();
  const [shown, setShown] = useState(reduce ? value : 0);
  useEffect(() => {
    if (reduce) { setShown(value); return; }
    const c = animate(0, value, { duration: 1.2, ease: "easeOut", onUpdate: setShown });
    return () => c.stop();
  }, [value, reduce]);
  return <span>{shown.toLocaleString(undefined, { minimumFractionDigits: decimals, maximumFractionDigits: decimals })}{suffix}</span>;
}
