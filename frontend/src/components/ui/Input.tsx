import { forwardRef, type InputHTMLAttributes } from "react";
import { cn } from "@/utils/cn";

interface Props extends InputHTMLAttributes<HTMLInputElement> { label: string; error?: string }
export const Input = forwardRef<HTMLInputElement, Props>(({ label, error, className, id, ...rest }, ref) => {
  const fid = id ?? `in-${label.replace(/\s+/g, "-").toLowerCase()}`;
  return (
    <div className="space-y-1">
      <label htmlFor={fid} className="text-sm text-muted">{label}</label>
      <input ref={ref} id={fid} aria-invalid={!!error} className={cn("focus-ring w-full rounded-xl border bg-surface/50 px-3 py-2 text-ink placeholder:text-muted/60 transition-[border-color,background-color,box-shadow] duration-200 hover:border-electric/40 focus:border-electric focus:bg-surface/80", error ? "border-danger" : "border-line", className)} {...rest} />
      {error && <p className="text-xs text-danger">{error}</p>}
    </div>
  );
});
Input.displayName = "Input";
