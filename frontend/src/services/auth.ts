import { api, patch, post } from "./api";
import type { AuditEntry, Member, Message, Org, TokenOut, User } from "@/types/auth";

export const authApi = {
  register: (b: { email: string; password: string; full_name: string; organization_name: string }) => post<TokenOut>("/auth/register", b),
  login: (b: { email: string; password: string }) => post<TokenOut>("/auth/login", b),
  refresh: () => post<TokenOut>("/auth/refresh"),
  logout: () => post<void>("/auth/logout"),
  verify: (token: string) => post<Message>("/auth/verify-email", { token }),
  resend: () => post<Message>("/auth/resend-verification"),
  forgot: (email: string) => post<Message>("/auth/forgot-password", { email }),
  reset: (token: string, new_password: string) => post<Message>("/auth/reset-password", { token, new_password }),
  updateMe: (b: { full_name?: string; phone?: string }) => patch<User>("/auth/me", b),
  updateOrg: (b: Record<string, unknown>) => patch<Org>("/organization", b),
  members: () => api<Member[]>("/users"),
  invite: (b: { email: string; full_name: string; role: string }) => post<Message>("/users/invite", b),
  updateMember: (id: string, b: { role?: string; is_active?: boolean }) => patch<Member>(`/users/${id}`, b),
  audit: (limit: number, offset: number) => api<AuditEntry[]>(`/audit-logs?limit=${limit}&offset=${offset}`),
};
