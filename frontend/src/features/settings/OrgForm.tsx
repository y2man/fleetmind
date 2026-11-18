import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { Button, Input } from "@/components/ui";
import { orgSchema, type OrgValues } from "@/schemas/auth";
import { authApi } from "@/services/auth";
import { useAuth } from "@/store/auth";
import { FormError } from "@/features/auth/AuthLayout";

export function OrgForm({ onSaved, submitLabel = "Save organization" }: { onSaved?: () => void; submitLabel?: string }) {
  const user = useAuth((s) => s.user)!;
  const o = user.organization;
  const f = useForm<OrgValues>({
    resolver: zodResolver(orgSchema),
    defaultValues: { name: o.name, country: o.country ?? "", timezone: o.timezone ?? Intl.DateTimeFormat().resolvedOptions().timeZone, fleet_size: o.fleet_size ?? undefined },
  });
  const m = useMutation({
    mutationFn: (v: OrgValues) => authApi.updateOrg({ ...v, fleet_size: v.fleet_size ?? null }),
    onSuccess: (org) => { useAuth.getState().patchUser({ organization: org }); onSaved?.(); },
  });
  const e = f.formState.errors;
  return (
    <form className="space-y-4" onSubmit={f.handleSubmit((v) => m.mutate(v))} noValidate>
      <Input label="Organization name" error={e.name?.message} {...f.register("name")} />
      <div className="grid gap-4 sm:grid-cols-3">
        <Input label="Country" error={e.country?.message} {...f.register("country")} />
        <Input label="Time zone" error={e.timezone?.message} {...f.register("timezone")} />
        <Input label="Fleet size" type="number" error={e.fleet_size?.message} {...f.register("fleet_size")} />
      </div>
      <FormError message={m.error?.message} />
      {m.isSuccess && !onSaved && <p className="text-sm text-ok">Saved.</p>}
      <Button type="submit" disabled={m.isPending}>{m.isPending ? "Saving…" : submitLabel}</Button>
    </form>
  );
}
