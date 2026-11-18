import { useQuery } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { Button, Input, Select } from "@/components/ui";
import { FormError } from "@/features/auth/AuthLayout";
import { options as loadOptions } from "@/services/resources";
import { toLocalInput } from "./format";
import type { Field } from "./types";

type Values = Record<string, string>;

function toForm(fields: Field[], row: Record<string, unknown> | null, defaults: Record<string, string>): Values {
  const v: Values = {};
  for (const f of fields) {
    const raw = row ? row[f.name] : defaults[f.name];
    if (raw === null || raw === undefined || raw === "") v[f.name] = "";
    else if (f.type === "datetime" && row) v[f.name] = toLocalInput(String(raw));
    else v[f.name] = String(raw);
  }
  return v;
}

/** Empty optional values are omitted on create and sent as null on edit (to clear them). */
function toPayload(fields: Field[], v: Values, editing: boolean): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const f of fields) {
    const s = (v[f.name] ?? "").trim();
    if (s === "") { if (editing && !f.required) out[f.name] = null; continue; }
    out[f.name] = f.type === "number" ? Number(s) : f.type === "datetime" ? new Date(s).toISOString() : s;
  }
  return out;
}

const rules = (f: Field, editing: boolean) => ({
  required: f.required && !(f.optionalOnCreate && !editing) ? `${f.label} is required` : false,
  validate: (val: string) => {
    const s = (val ?? "").trim();
    if (!s) return true;
    if (f.type === "number") {
      const n = Number(s);
      if (!Number.isFinite(n)) return "Enter a number";
      if (f.int && !Number.isInteger(n)) return "Enter a whole number";
      if (f.min !== undefined && n < f.min) return `Must be at least ${f.min}`;
      if (f.max !== undefined && n > f.max) return `Must be at most ${f.max}`;
    }
    if (f.type === "email" && !/^\S+@\S+\.\S+$/.test(s)) return "Enter a valid email";
    if ((f.type === "date" || f.type === "datetime") && Number.isNaN(new Date(s).getTime())) return "Enter a valid date";
    return true;
  },
});

interface Props {
  fields: Field[];
  row: Record<string, unknown> | null;
  defaults: Record<string, string>;
  pending: boolean;
  error?: string;
  onSubmit: (payload: Record<string, unknown>) => void;
  onCancel: () => void;
}

export function ResourceForm({ fields, row, defaults, pending, error, onSubmit, onCancel }: Props) {
  const editing = row !== null;
  const { register, handleSubmit, formState: { errors } } = useForm<Values>({ defaultValues: toForm(fields, row, defaults) });
  const vehicles = useQuery({ queryKey: ["options", "vehicles"], queryFn: () => loadOptions("vehicles"), enabled: fields.some((f) => f.type === "vehicle") });
  const drivers = useQuery({ queryKey: ["options", "drivers"], queryFn: () => loadOptions("drivers"), enabled: fields.some((f) => f.type === "driver") });
  const toChoices = (d?: { id: string; label: string }[]) => (d ?? []).map((o) => ({ value: o.id, label: o.label }));

  return (
    <form className="grid gap-4 sm:grid-cols-2" onSubmit={handleSubmit((v) => onSubmit(toPayload(fields, v, editing)))} noValidate>
      {fields.map((f) => {
        const err = errors[f.name]?.message as string | undefined;
        const label = f.required && !(f.optionalOnCreate && !editing) ? `${f.label} *` : f.label;
        const reg = register(f.name, rules(f, editing));
        const wrap = f.full || f.type === "textarea" ? "sm:col-span-2" : "";
        let control;
        if (f.type === "select") {
          control = <Select label={label} error={err} options={f.options ?? []} placeholder={f.required ? undefined : "None"} {...reg} />;
        } else if (f.type === "vehicle" || f.type === "driver") {
          const q = f.type === "vehicle" ? vehicles : drivers;
          const noun = f.type;
          control = <Select label={label} error={err ?? (q.isError ? `Could not load ${noun}s` : undefined)} options={toChoices(q.data)} placeholder={q.isLoading ? "Loading…" : f.required ? `Select a ${noun}` : "None"} {...reg} />;
        } else if (f.type === "textarea") {
          control = (
            <div className="space-y-1">
              <label htmlFor={`f-${f.name}`} className="text-sm text-muted">{label}</label>
              <textarea id={`f-${f.name}`} rows={3} maxLength={f.maxLength} aria-invalid={!!err} className="focus-ring w-full rounded-xl border border-line bg-bg/60 px-3 py-2 text-ink" {...reg} />
              {err && <p className="text-xs text-danger">{err}</p>}
            </div>
          );
        } else {
          const type = f.type === "datetime" ? "datetime-local" : f.type === "number" ? "number" : f.type;
          control = <Input id={`f-${f.name}`} label={label} type={type} step={f.type === "number" ? (f.int ? 1 : "any") : undefined} maxLength={f.maxLength} error={err} {...reg} />;
        }
        return (
          <div key={f.name} className={wrap}>
            {control}
            {f.hint && !err && <p className="mt-1 text-xs text-muted">{f.hint}</p>}
          </div>
        );
      })}
      <div className="space-y-3 sm:col-span-2">
        <FormError message={error} />
        <div className="flex justify-end gap-2">
          <Button type="button" variant="ghost" onClick={onCancel}>Cancel</Button>
          <Button type="submit" disabled={pending}>{pending ? "Saving…" : editing ? "Save changes" : "Create"}</Button>
        </div>
      </div>
    </form>
  );
}
