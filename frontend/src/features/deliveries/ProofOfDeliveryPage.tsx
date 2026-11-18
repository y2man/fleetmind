import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Download, FilePlus2, Trash2 } from "lucide-react";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Button, GlassCard } from "@/components/ui";
import { FormError } from "@/features/auth/AuthLayout";
import { api, download } from "@/services/api";
import { useAuth } from "@/store/auth";
import type { DeliveryDocument } from "@/types/fleet";

const ACCEPTED_TYPES = "application/pdf,image/jpeg,image/png,image/webp";

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function ProofOfDeliveryPage() {
  const { deliveryId = "" } = useParams();
  const { can } = useAuth();
  const canWrite = can("deliveries:write");
  const client = useQueryClient();
  const [file, setFile] = useState<File | null>(null);
  const basePath = `/deliveries/${deliveryId}/proof`;

  const documents = useQuery({
    queryKey: ["delivery-proof", deliveryId],
    queryFn: () => api<DeliveryDocument[]>(basePath),
    enabled: Boolean(deliveryId),
  });
  const upload = useMutation({
    mutationFn: (selected: File) => api<DeliveryDocument>(
      `${basePath}?filename=${encodeURIComponent(selected.name)}`,
      { method: "POST", headers: { "Content-Type": selected.type }, body: selected },
    ),
    onSuccess: async () => {
      setFile(null);
      await client.invalidateQueries({ queryKey: ["delivery-proof", deliveryId] });
    },
  });
  const remove = useMutation({
    mutationFn: (doc: DeliveryDocument) => api<void>(`${basePath}/${doc.id}`, { method: "DELETE" }),
    onSuccess: async () => client.invalidateQueries({ queryKey: ["delivery-proof", deliveryId] }),
  });
  const getFile = useMutation({
    mutationFn: (doc: DeliveryDocument) => download(`${basePath}/${doc.id}/content`, doc.filename),
  });

  const error = documents.error?.message ?? upload.error?.message ?? remove.error?.message ?? getFile.error?.message;

  return (
    <div className="space-y-6">
      <Link to="/app/deliveries" className="inline-flex items-center gap-2 text-sm text-muted hover:text-ink">
        <ArrowLeft size={16} /> Back to deliveries
      </Link>
      <div>
        <h1 className="text-gradient text-3xl font-extrabold">Proof of delivery</h1>
        <p className="text-muted">Files stay in private storage and are only available to your organization.</p>
      </div>

      <GlassCard hover={false} className="space-y-4">
        {canWrite && (
          <form className="flex flex-wrap items-end gap-3" onSubmit={(event) => {
            event.preventDefault();
            if (file) upload.mutate(file);
          }}>
            <label className="min-w-60 flex-1 space-y-1 text-sm">
              <span>Receipt, signature or delivery photo (PDF, JPEG, PNG, WebP)</span>
              <input
                type="file"
                accept={ACCEPTED_TYPES}
                onChange={(event) => setFile(event.target.files?.[0] ?? null)}
                className="focus-ring block w-full rounded-xl border border-line bg-bg/60 p-2 text-ink"
              />
            </label>
            <Button type="submit" disabled={!file || upload.isPending}>
              <FilePlus2 size={16} />{upload.isPending ? "Uploading…" : "Upload proof"}
            </Button>
          </form>
        )}
        <FormError message={error} />

        {documents.isLoading ? <p className="text-sm text-muted">Loading proof files…</p> : null}
        {!documents.isLoading && documents.data?.length === 0 ? <p className="text-sm text-muted">No proof files uploaded yet.</p> : null}
        {!!documents.data?.length && (
          <ul className="divide-y divide-line">
            {documents.data.map((doc) => (
              <li key={doc.id} className="flex flex-wrap items-center justify-between gap-3 py-3">
                <div className="min-w-0">
                  <p className="truncate font-medium">{doc.filename}</p>
                  <p className="text-xs text-muted">{formatSize(doc.size_bytes)} · {new Date(doc.created_at).toLocaleString()}</p>
                </div>
                <div className="flex gap-2">
                  <Button size="sm" variant="outline" disabled={getFile.isPending} onClick={() => getFile.mutate(doc)}>
                    <Download size={15} />Download
                  </Button>
                  {canWrite && (
                    <Button size="sm" variant="danger" disabled={remove.isPending} aria-label={`Delete ${doc.filename}`}
                      onClick={() => { if (window.confirm(`Delete ${doc.filename}?`)) remove.mutate(doc); }}>
                      <Trash2 size={15} />
                    </Button>
                  )}
                </div>
              </li>
            ))}
          </ul>
        )}
      </GlassCard>
    </div>
  );
}
