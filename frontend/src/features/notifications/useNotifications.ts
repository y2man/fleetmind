import { useEffect } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { notificationsApi } from "@/services/analytics";
import { useAuth } from "@/store/auth";

const RECHECK_MS = 5 * 60_000;

/** Notification list + actions. The smart-alert rules run when the app opens and every few minutes. */
export function useNotifications(limit = 30, unreadOnly = false) {
  const qc = useQueryClient();
  const enabled = useAuth((s) => s.can("analytics:read"));
  const key = ["notifications", limit, unreadOnly];
  const invalidate = () => qc.invalidateQueries({ queryKey: ["notifications"] });

  const list = useQuery({ queryKey: key, queryFn: () => notificationsApi.list({ limit, unreadOnly }), enabled, refetchInterval: 60_000 });
  const refresh = useMutation({ mutationFn: notificationsApi.refresh, onSuccess: invalidate });
  const read = useMutation({ mutationFn: notificationsApi.read, onSuccess: invalidate });
  const readAll = useMutation({ mutationFn: notificationsApi.readAll, onSuccess: invalidate });

  return { list, refresh, read, readAll, enabled };
}

/** Mount once (in the app shell) to keep alerts current. A failed check is silent; the bell still shows saved alerts. */
export function useAlertSweep() {
  const qc = useQueryClient();
  const enabled = useAuth((s) => s.can("analytics:read"));
  const { mutate } = useMutation({ mutationFn: notificationsApi.refresh, onSuccess: () => qc.invalidateQueries({ queryKey: ["notifications"] }) });
  useEffect(() => {
    if (!enabled) return;
    mutate();
    const t = setInterval(() => mutate(), RECHECK_MS);
    return () => clearInterval(t);
  }, [enabled, mutate]);
}
