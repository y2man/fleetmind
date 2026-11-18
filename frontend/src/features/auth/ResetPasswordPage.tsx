import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { Link, useSearchParams } from "react-router-dom";
import type { z } from "zod";
import { Button, Input } from "@/components/ui";
import { resetSchema } from "@/schemas/auth";
import { authApi } from "@/services/auth";
import { AuthLayout, FormError } from "./AuthLayout";

type V = z.infer<typeof resetSchema>;
export function ResetPasswordPage() {
  const token = useSearchParams()[0].get("token") ?? "";
  const f = useForm<V>({ resolver: zodResolver(resetSchema) });
  const e = f.formState.errors;
  const m = useMutation({ mutationFn: (v: V) => authApi.reset(token, v.new_password) });
  return (
    <AuthLayout title="Choose a new password">
      {!token ? <FormError message="This link is missing its token. Request a new one." /> : m.isSuccess ? (
        <p className="text-ok">{m.data.message}. <Link className="text-electric underline" to="/signin">Sign in</Link></p>
      ) : (
        <form className="space-y-4" onSubmit={f.handleSubmit((v) => m.mutate(v))} noValidate>
          <Input label="New password" type="password" autoComplete="new-password" error={e.new_password?.message} {...f.register("new_password")} />
          <Input label="Confirm password" type="password" autoComplete="new-password" error={e.confirm?.message} {...f.register("confirm")} />
          <FormError message={m.error?.message} />
          <Button type="submit" className="w-full" disabled={m.isPending}>{m.isPending ? "Saving…" : "Update password"}</Button>
        </form>
      )}
    </AuthLayout>
  );
}
