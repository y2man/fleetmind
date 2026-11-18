import { create } from "zustand";
import { authApi } from "@/services/auth";
import { setAccessToken, setRefresher } from "@/services/api";
import type { TokenOut, User } from "@/types/auth";

interface AuthState {
  user: User | null;
  status: "loading" | "authed" | "anon";
  setSession: (t: TokenOut) => void;
  patchUser: (u: Partial<User>) => void;
  bootstrap: () => Promise<void>;
  logout: () => Promise<void>;
  can: (permission: string) => boolean;
}

let inflight: Promise<string | null> | null = null;

export const useAuth = create<AuthState>((set, get) => ({
  user: null,
  status: "loading",
  setSession: (t) => { setAccessToken(t.access_token); set({ user: t.user, status: "authed" }); },
  patchUser: (u) => set((s) => (s.user ? { user: { ...s.user, ...u } } : s)),
  bootstrap: async () => {
    try { get().setSession(await authApi.refresh()); } catch { setAccessToken(null); set({ user: null, status: "anon" }); }
  },
  logout: async () => {
    try { await authApi.logout(); } catch { /* cookie may already be gone */ }
    setAccessToken(null);
    set({ user: null, status: "anon" });
  },
  can: (p) => !!get().user?.permissions.includes(p),
}));

setRefresher(() => {
  inflight ??= authApi.refresh().then((t) => { useAuth.getState().setSession(t); return t.access_token; }).catch(() => { useAuth.setState({ user: null, status: "anon" }); return null; }).finally(() => { inflight = null; });
  return inflight;
});
