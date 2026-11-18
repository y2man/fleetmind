import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { Link, useLocation, useNavigate } from "react-router-dom";
import type { z } from "zod";
import { Button, Input } from "@/components/ui";
import { DEMO_LOGIN } from "@/config/env";
import { DEMO_ACCOUNTS, DEMO_PASSWORD } from "@/config/demo";
import { signInSchema } from "@/schemas/auth";
import { authApi } from "@/services/auth";
import { useAuth } from "@/store/auth";
import { AuthLayout, FormError } from "./AuthLayout";

type V = z.infer<typeof signInSchema>;
export function SignInPage() {
  const nav = useNavigate();
  const from = (useLocation().state as { from?: string } | null)?.from ?? "/app/dashboard";
  const setSession = useAuth((s) => s.setSession);
  const f = useForm<V>({ resolver: zodResolver(signInSchema) });
  const m = useMutation({ mutationFn: (v: V) => authApi.login(v), onSuccess: (t) => { setSession(t); nav(from, { replace: true }); } });
  return (
    <AuthLayout title="Welcome back" subtitle="Sign in to your FleetMind workspace.">
      <form className="auth-fields space-y-4" onSubmit={f.handleSubmit((v) => m.mutate(v))} noValidate>
        <Input label="Email" type="email" autoComplete="email" error={f.formState.errors.email?.message} {...f.register("email")} />
        <Input label="Password" type="password" autoComplete="current-password" error={f.formState.errors.password?.message} {...f.register("password")} />
        <FormError message={m.error?.message} />
        <Button type="submit" className="w-full" disabled={m.isPending}>{m.isPending ? "Signing in…" : "Sign in"}</Button>
      </form>
      {DEMO_LOGIN && (
        <div className="rounded-xl border border-line p-3">
          <p className="text-sm font-medium">Try the demo</p>
          <p className="mt-1 text-xs text-muted">Fictional data. Pick a role to fill in the form, then press Sign in.</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {DEMO_ACCOUNTS.map((a) => (
              <Button key={a.role} type="button" variant="outline" size="sm" onClick={() => { f.setValue("email", a.email); f.setValue("password", DEMO_PASSWORD); }}>{a.role}</Button>
            ))}
          </div>
        </div>
      )}
      <p className="text-sm text-muted"><Link className="text-electric underline" to="/forgot-password">Forgot password?</Link> · <Link className="text-electric underline" to="/signup">Create an account</Link></p>
    </AuthLayout>
  );
}
