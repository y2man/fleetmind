import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { Link, useNavigate } from "react-router-dom";
import { Button, Input } from "@/components/ui";
import { signUpSchema, type SignUpValues } from "@/schemas/auth";
import { authApi } from "@/services/auth";
import { useAuth } from "@/store/auth";
import { AuthLayout, FormError } from "./AuthLayout";

export function SignUpPage() {
  const nav = useNavigate();
  const setSession = useAuth((s) => s.setSession);
  const f = useForm<SignUpValues>({ resolver: zodResolver(signUpSchema) });
  const e = f.formState.errors;
  const m = useMutation({
    mutationFn: ({ confirm: _c, ...v }: SignUpValues) => authApi.register(v),
    onSuccess: (t) => { setSession(t); nav("/app/onboarding", { replace: true }); },
  });
  return (
    <AuthLayout title="Create your account" subtitle="You’ll become the owner of a new organization.">
      <form className="auth-fields space-y-4" onSubmit={f.handleSubmit((v) => m.mutate(v))} noValidate>
        <Input label="Full name" autoComplete="name" error={e.full_name?.message} {...f.register("full_name")} />
        <Input label="Organization name" error={e.organization_name?.message} {...f.register("organization_name")} />
        <Input label="Work email" type="email" autoComplete="email" error={e.email?.message} {...f.register("email")} />
        <Input label="Password" type="password" autoComplete="new-password" error={e.password?.message} {...f.register("password")} />
        <Input label="Confirm password" type="password" autoComplete="new-password" error={e.confirm?.message} {...f.register("confirm")} />
        <FormError message={m.error?.message} />
        <Button type="submit" className="w-full" disabled={m.isPending}>{m.isPending ? "Creating…" : "Create account"}</Button>
      </form>
      <p className="text-sm text-muted">Already have an account? <Link className="text-electric underline" to="/signin">Sign in</Link></p>
    </AuthLayout>
  );
}
