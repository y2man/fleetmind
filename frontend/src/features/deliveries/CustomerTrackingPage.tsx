import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Copy, Link2, ShieldOff } from "lucide-react";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Button, GlassCard, Input } from "@/components/ui";
import { FormError } from "@/features/auth/AuthLayout";
import { api, del, post } from "@/services/api";

interface LinkRecord {
  id: string;
  created_at: string;
  expires_at: string;
  revoked_at: string | null;
}

interface CreatedLink {
  id: string;
  url: string;
  expires_at: string;
}

export function CustomerTrackingPage() {
  const { deliveryId = "" } = useParams();
  const client = useQueryClient();
  const [ttlHours, setTtlHours] = useState("168");
  const [createdUrl, setCreatedUrl] = useState("");
  const linksPath = `/deliveries/${deliveryId}/tracking-links`;
  const links = useQuery({
    queryKey: ["customer-tracking-links", deliveryId],
    queryFn: () => api<LinkRecord[]>(linksPath),
    enabled: Boolean(deliveryId),
  });
  const create = useMutation({
    mutationFn: () => post<CreatedLink>(linksPath, { ttl_hours: Number(ttlHours) }),
    onSuccess: async (result) => {
      setCreatedUrl(result.url);
      await client.invalidateQueries({ queryKey: ["customer-tracking-links", deliveryId] });
    },
  });
  const revoke = useMutation({
    mutationFn: (id: string) => del(`${linksPath}/${id}`),
    onSuccess: async () => client.invalidateQueries({ queryKey: ["customer-tracking-links", deliveryId] }),
  });
  const error = links.error?.message ?? create.error?.message ?? revoke.error?.message;

  return (
    <div className="space-y-6">
      <Link to="/app/deliveries" className="text-sm text-muted hover:text-ink">← Back to deliveries</Link>
      <div>
        <h1 className="text-gradient text-3xl font-extrabold">Customer tracking links</h1>
        <p className="text-muted">Share a private, expiring read-only link for this delivery.</p>
      </div>
      <GlassCard hover={false} className="space-y-4">
        <div className="flex flex-wrap items-end gap-3">
          <Input label="Link lifetime (hours)" type="number" min={1} max={2160} value={ttlHours}
            onChange={(event) => setTtlHours(event.target.value)} />
          <Button disabled={!Number.isInteger(Number(ttlHours)) || Number(ttlHours) < 1 || Number(ttlHours) > 2160 || create.isPending}
            onClick={() => create.mutate()}>
            <Link2 size={16} />{create.isPending ? "Creating…" : "Create tracking link"}
          </Button>
        </div>
        {createdUrl && (
          <div className="space-y-2 rounded-xl border border-line bg-bg/50 p-3">
            <p className="text-sm font-medium">Copy this link now. The secret is not shown again.</p>
            <div className="flex flex-wrap gap-2">
              <input aria-label="New customer tracking URL" readOnly value={createdUrl}
                className="focus-ring min-w-48 flex-1 rounded-lg border border-line bg-bg px-3 py-2 text-sm" />
              <Button variant="outline" onClick={() => void navigator.clipboard.writeText(createdUrl)}><Copy size={15} />Copy</Button>
            </div>
          </div>
        )}
        <FormError message={error} />
        {links.isLoading ? <p className="text-sm text-muted">Loading links…</p> : null}
        {!!links.data?.length && (
          <ul className="divide-y divide-line">
            {links.data.map((item) => {
              const expired = Date.parse(item.expires_at) <= Date.now();
              const inactive = Boolean(item.revoked_at) || expired;
              return (
                <li key={item.id} className="flex flex-wrap items-center justify-between gap-3 py-3 text-sm">
                  <div>
                    <p className="font-medium">{item.revoked_at ? "Revoked" : expired ? "Expired" : "Active"}</p>
                    <p className="text-xs text-muted">Expires {new Date(item.expires_at).toLocaleString()}</p>
                  </div>
                  {!inactive && (
                    <Button size="sm" variant="outline" disabled={revoke.isPending} onClick={() => revoke.mutate(item.id)}>
                      <ShieldOff size={15} />Revoke
                    </Button>
                  )}
                </li>
              );
            })}
          </ul>
        )}
        {!links.isLoading && links.data?.length === 0 && <p className="text-sm text-muted">No tracking links for this delivery.</p>}
      </GlassCard>
    </div>
  );
}
