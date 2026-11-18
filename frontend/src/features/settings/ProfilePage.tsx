import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { Badge, Button, GlassCard, Input } from "@/components/ui";
import { DevLink, FormError } from "@/features/auth/AuthLayout";
import { profileSchema } from "@/schemas/auth";
import { authApi } from "@/services/auth";
import { useAuth } from "@/store/auth";
import type { z } from "zod";
import { OrgForm } from "./OrgForm";

type V = z.infer<typeof profileSchema>;
export function ProfilePage() {
  const { user, can } = useAuth();
  const u = user!;
  const f = useForm<V>({ resolver: zodResolver(profileSchema), defaultValues: { full_name: u.full_name, phone: u.phone ?? "" } });
  const save = useMutation({ mutationFn: (v: V) => authApi.updateMe(v), onSuccess: (nu) => useAuth.getState().patchUser(nu) });
  const resend = useMutation({ mutationFn: authApi.resend });
  return (
    <div className="max-w-2xl space-y-6">
      <div><h1 className="text-gradient text-3xl font-extrabold">Profile</h1><p className="text-muted">{u.email} · <Badge>{u.role}</Badge></p></div>
      {!u.email_verified && (
        <GlassCard hover={false} className="space-y-2">
          <p className="text-warn">Your email isn’t verified yet.</p>
          <Button variant="outline" size="sm" onClick={() => resend.mutate()} disabled={resend.isPending}>Resend verification email</Button>
          {resend.isSuccess && <p className="text-sm text-ok">{resend.data.message}</p>}
          <DevLink link={resend.data?.dev_link} /><FormError message={resend.error?.message} />
        </GlassCard>
      )}
      <GlassCard hover={false}>
        <h2 className="mb-4 font-semibold">Your details</h2>
        <form className="space-y-4" onSubmit={f.handleSubmit((v) => save.mutate(v))} noValidate>
          <Input label="Full name" error={f.formState.errors.full_name?.message} {...f.register("full_name")} />
          <Input label="Phone" {...f.register("phone")} />
          <FormError message={save.error?.message} />
          {save.isSuccess && <p className="text-sm text-ok">Saved.</p>}
          <Button type="submit" disabled={save.isPending}>Save profile</Button>
        </form>
      </GlassCard>
      {can("org:manage") ? <GlassCard hover={false}><h2 className="mb-4 font-semibold">Organization</h2><OrgForm /></GlassCard>
        : <p className="text-sm text-muted">Organization: {u.organization.name}. Only the owner can edit it.</p>}
    </div>
  );
}
