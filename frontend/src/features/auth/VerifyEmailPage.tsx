import { useQuery } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";
import { Skeleton } from "@/components/ui";
import { authApi } from "@/services/auth";
import { AuthLayout, FormError } from "./AuthLayout";

export function VerifyEmailPage() {
  const token = useSearchParams()[0].get("token") ?? "";
  const q = useQuery({ queryKey: ["verify", token], queryFn: () => authApi.verify(token), enabled: !!token, retry: false, staleTime: Infinity });
  return (
    <AuthLayout title="Email verification">
      {!token && <FormError message="This link is missing its token." />}
      {q.isLoading && <Skeleton className="h-6 w-48" />}
      {q.isError && <FormError message={q.error.message} />}
      {q.isSuccess && <p className="text-ok">Your email is verified.</p>}
      <Link className="text-sm text-electric underline" to="/app/dashboard">Continue to FleetMind</Link>
    </AuthLayout>
  );
}
