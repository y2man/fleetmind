import { forwardRef, type SelectHTMLAttributes } from "react";
import { cn } from "@/utils/cn";

interface Props extends SelectHTMLAttributes<HTMLSelectElement> { label: string; error?: string; options: { value: string; label: string }[]; placeholder?: string }

/** Native select: accessible by default and works with react-hook-form's register(). */
export const Select = forwardRef<HTMLSelectElement, Props>(({ label, error, options, placeholder, className, id, ...rest }, ref) => {
  const fid = id ?? `sel-${label.replace(/\s+/g, "-").toLowerCase()}`;
  return (
    <div className="space-y-1">
      <label htmlFor={fid} className="text-sm text-muted">{label}</label>
      <select ref={ref} id={fid} aria-invalid={!!error} className={cn("focus-ring w-full rounded-xl border bg-bg px-3 py-2 text-ink", error ? "border-danger" : "border-line", className)} {...rest}>
        {placeholder !== undefined && <option value="">{placeholder}</option>}
        {options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
      {error && <p className="text-xs text-danger">{error}</p>}
    </div>
  );
});
Select.displayName = "Select";
