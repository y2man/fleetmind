import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Button, GlassCard, Skeleton } from "@/components/ui";
import { FormError } from "@/features/auth/AuthLayout";
import { authApi } from "@/services/auth";

const SIZE = 20;
export function AuditPage() {
  const [page, setPage] = useState(0);
  const q = useQuery({ queryKey: ["audit", page], queryFn: () => authApi.audit(SIZE, page * SIZE), placeholderData: (p) => p });
  return (
    <div className="space-y-6">
      <div><h1 className="text-gradient text-3xl font-extrabold">Audit log</h1><p className="text-muted">Security-relevant events in your organization.</p></div>
      <GlassCard hover={false} className="overflow-x-auto">
        {q.isLoading ? <Skeleton className="h-32" /> : q.isError ? <FormError message={q.error.message} /> : (
          <table className="w-full text-left text-sm">
            <thead className="text-muted"><tr><th className="p-2">When</th><th>Action</th><th>Entity</th><th>IP</th></tr></thead>
            <tbody>{q.data!.map((a) => <tr key={a.id} className="border-t border-line"><td className="p-2">{new Date(a.created_at).toLocaleString()}</td><td>{a.action}</td><td>{a.entity_type ?? "–"}</td><td>{a.ip ?? "–"}</td></tr>)}</tbody>
          </table>)}
        <div className="mt-4 flex gap-2">
          <Button variant="outline" size="sm" disabled={page === 0} onClick={() => setPage((p) => p - 1)}>Previous</Button>
          <Button variant="outline" size="sm" disabled={(q.data?.length ?? 0) < SIZE} onClick={() => setPage((p) => p + 1)}>Next</Button>
        </div>
      </GlassCard>
    </div>
  );
}
