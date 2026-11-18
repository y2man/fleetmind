import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useForm } from "react-hook-form";
import type { z } from "zod";
import { Badge, Button, Dropdown, GlassCard, Input, Modal, Skeleton } from "@/components/ui";
import { DevLink, FormError } from "@/features/auth/AuthLayout";
import { inviteSchema } from "@/schemas/auth";
import { authApi } from "@/services/auth";
import { useAuth } from "@/store/auth";

type V = z.infer<typeof inviteSchema>;
const ROLES = [{ value: "admin", label: "Admin" }, { value: "dispatcher", label: "Dispatcher" }, { value: "viewer", label: "Viewer" }];

export function TeamPage() {
  const { can, user } = useAuth();
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const q = useQuery({ queryKey: ["team"], queryFn: authApi.members });
  const upd = useMutation({ mutationFn: (a: { id: string; role?: string; is_active?: boolean }) => authApi.updateMember(a.id, a), onSuccess: () => qc.invalidateQueries({ queryKey: ["team"] }) });
  const f = useForm<V>({ resolver: zodResolver(inviteSchema), defaultValues: { role: "viewer" } });
  const inv = useMutation({ mutationFn: (v: V) => authApi.invite(v), onSuccess: () => { qc.invalidateQueries({ queryKey: ["team"] }); f.reset({ role: "viewer", email: "", full_name: "" }); } });
  const manage = can("users:manage");
  const canEdit = (role: string, id: string) => manage && id !== user?.id && role !== "owner" && (role !== "admin" || user?.role === "owner");
  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between"><div><h1 className="text-gradient text-3xl font-extrabold">Team</h1><p className="text-muted">People in {user?.organization.name}</p></div>
        {manage && <Button onClick={() => { inv.reset(); setOpen(true); }}>Invite member</Button>}</div>
      <GlassCard hover={false} className="overflow-x-auto">
        {q.isLoading ? <Skeleton className="h-24" /> : q.isError ? <FormError message={q.error.message} /> : (
          <table className="w-full text-left text-sm">
            <thead className="text-muted"><tr><th className="p-2">Name</th><th>Email</th><th>Role</th><th>Status</th><th /></tr></thead>
            <tbody>{q.data!.map((m) => (
              <tr key={m.id} className="border-t border-line">
                <td className="p-2">{m.full_name}</td><td>{m.email}</td>
                <td>{canEdit(m.role_name, m.id) ? <Dropdown label="Role" options={user?.role === "owner" ? ROLES : ROLES.slice(1)} value={m.role_name} onChange={(role) => upd.mutate({ id: m.id, role })} /> : <Badge>{m.role_name}</Badge>}</td>
                <td><Badge tone={m.is_active ? "ok" : "danger"}>{m.is_active ? "Active" : "Disabled"}</Badge></td>
                <td>{canEdit(m.role_name, m.id) && <Button size="sm" variant="ghost" onClick={() => upd.mutate({ id: m.id, is_active: !m.is_active })}>{m.is_active ? "Disable" : "Enable"}</Button>}</td>
              </tr>))}</tbody>
          </table>)}
        <FormError message={upd.error?.message} />
      </GlassCard>
      <Modal open={open} onClose={() => setOpen(false)} title="Invite a team member">
        <form className="space-y-4" onSubmit={f.handleSubmit((v) => inv.mutate(v))} noValidate>
          <Input label="Full name" error={f.formState.errors.full_name?.message} {...f.register("full_name")} />
          <Input label="Email" type="email" error={f.formState.errors.email?.message} {...f.register("email")} />
          <div><p className="mb-1 text-sm text-muted">Role</p><Dropdown label="Role" options={user?.role === "owner" ? ROLES : ROLES.slice(1)} value={f.watch("role")} onChange={(v) => f.setValue("role", v as V["role"])} /></div>
          <FormError message={inv.error?.message} />
          {inv.isSuccess && <p className="text-sm text-ok">{inv.data.message}</p>}
          <DevLink link={inv.data?.dev_link} />
          <Button type="submit" disabled={inv.isPending}>Send invitation</Button>
        </form>
      </Modal>
    </div>
  );
}
