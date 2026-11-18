import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "@/services/api";
import type { Health } from "@/types/health";
import { GlassCard, Skeleton, Badge } from "@/components/ui";

export function StatusPage() {
  const { data, isLoading, isError } = useQuery({ queryKey: ["health"], queryFn: () => api<Health>("/health") });
  return (
    <main className="grid min-h-screen place-items-center p-6">
      <GlassCard className="w-full max-w-md" hover={false}>
        <h1 className="text-gradient text-3xl font-extrabold">FleetMind</h1>
        <p className="mt-1 text-muted">Application status</p>
        <div className="mt-6 space-y-3">
          {isLoading && <Skeleton className="h-6 w-40" />}
          {isError && <Badge tone="danger">API unreachable</Badge>}
          {data && (<>
            <Badge tone="ok">API {data.status}</Badge>
            <p className="text-sm text-muted">AI service: {data.ai_configured ? "configured" : "not configured"}</p>
          </>)}
        </div>
        <Link to="/" className="focus-ring mt-6 inline-block text-electric underline">Back to home</Link>
      </GlassCard>
    </main>
  );
}
