import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useRef, useState } from "react";
import { Check, ChevronDown } from "lucide-react";

export interface Option { value: string; label: string }
interface Props { label: string; options: Option[]; value: string; onChange: (v: string) => void }

export function Dropdown({ label, options, value, onChange }: Props) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const click = (e: MouseEvent) => !ref.current?.contains(e.target as Node) && setOpen(false);
    const key = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("mousedown", click);
    document.addEventListener("keydown", key);
    return () => { document.removeEventListener("mousedown", click); document.removeEventListener("keydown", key); };
  }, []);
  const current = options.find((o) => o.value === value);

  return (
    <div ref={ref} className="relative inline-block">
      <button aria-haspopup="listbox" aria-expanded={open} aria-label={label} onClick={() => setOpen((o) => !o)}
        className="focus-ring glass flex items-center gap-2 rounded-xl px-3 py-2 text-sm">
        {current?.label ?? label}<ChevronDown size={16} className={open ? "rotate-180 transition" : "transition"} />
      </button>
      <AnimatePresence>
        {open && (
          <motion.ul role="listbox" initial={{ opacity: 0, y: -6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -6 }}
            className="glass absolute z-40 mt-2 min-w-40 rounded-xl p-1">
            {options.map((o) => (
              <li key={o.value} role="option" aria-selected={o.value === value}>
                <button onClick={() => { onChange(o.value); setOpen(false); }}
                  className="focus-ring flex w-full items-center justify-between rounded-lg px-3 py-2 text-left text-sm hover:bg-electric/15">
                  {o.label}{o.value === value && <Check size={14} className="text-electric" />}
                </button>
              </li>
            ))}
          </motion.ul>
        )}
      </AnimatePresence>
    </div>
  );
}
