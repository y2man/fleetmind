import { useEffect } from "react";
import { Navigate, Outlet, useLocation } from "react-router-dom";
import { Skeleton } from "@/components/ui";
import { useAuth } from "@/store/auth";

export function ProtectedRoute({ permission }: { permission?: string }) {
  const { status, bootstrap, can } = useAuth();
  const loc = useLocation();
  useEffect(() => { if (useAuth.getState().status === "loading") void bootstrap(); }, [bootstrap]);
  if (status === "loading") return <div className="p-8"><Skeleton className="h-8 w-64" /></div>;
  if (status === "anon") return <Navigate to="/signin" state={{ from: loc.pathname }} replace />;
  if (permission && !can(permission)) return <p className="p-8 text-muted">You don’t have access to this page.</p>;
  return <Outlet />;
}
