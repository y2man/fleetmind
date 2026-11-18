import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo } from "react";
import { api } from "@/services/api";
import { GlassCard } from "@/components/ui";

interface PublicTracking {
  reference: string;
  status: string;
  destination: string;
  deadline: string | null;
  delivered_at: string | null;
  updated_at: string;
  expires_at: string;
}

export function PublicTrackingPage() {
  const token = useMemo(() => {
    const value = new URLSearchParams(window.location.hash.slice(1)).get("token") ?? "";
    if (value) window.history.replaceState(null, "", window.location.pathname);
    return value;
  }, []);
  const result = useQuery({
    queryKey: ["public-tracking", token],
    queryFn: () => api<PublicTracking>("/public/tracking", { headers: { "X-Tracking-Token": token } }),
    enabled: Boolean(token),
    retry: false,
  });

  useEffect(() => { document.title = "Delivery tracking · FleetMind"; }, []);

  return (
    <main className="grid min-h-screen place-items-center p-4">
      <GlassCard hover={false} className="w-full max-w-xl space-y-4">
        <div className="flex items-center gap-2 text-gradient text-xl font-extrabold">
          <img src="/logo-mark.svg" alt="" className="h-8 w-8" />FleetMind
        </div>
        <h1 className="text-2xl font-bold">Delivery tracking</h1>
        {!token && <p role="alert" className="text-danger">This tracking link is invalid or incomplete.</p>}
        {result.isLoading && <p className="text-muted">Loading delivery status…</p>}
        {result.isError && <p role="alert" className="text-danger">This tracking link is invalid, revoked, or expired.</p>}
        {result.data && (
          <dl className="grid gap-3 sm:grid-cols-2">
            <div><dt className="text-xs text-muted">Reference</dt><dd className="font-semibold">{result.data.reference}</dd></div>
            <div><dt className="text-xs text-muted">Status</dt><dd className="font-semibold capitalize">{result.data.status.replace(/_/g, " ")}</dd></div>
            <div className="sm:col-span-2"><dt className="text-xs text-muted">Destination</dt><dd>{result.data.destination}</dd></div>
            <div><dt className="text-xs text-muted">Expected by</dt><dd>{result.data.deadline ? new Date(result.data.deadline).toLocaleString() : "Not available"}</dd></div>
            {result.data.delivered_at && <div><dt className="text-xs text-muted">Delivered at</dt><dd>{new Date(result.data.delivered_at).toLocaleString()}</dd></div>}
            <div className="sm:col-span-2 text-xs text-muted">Updated {new Date(result.data.updated_at).toLocaleString()} · Link expires {new Date(result.data.expires_at).toLocaleString()}</div>
          </dl>
        )}
      </GlassCard>
    </main>
  );
}
