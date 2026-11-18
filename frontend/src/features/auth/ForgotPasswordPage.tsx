import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { Link } from "react-router-dom";
import type { z } from "zod";
import { Button, Input } from "@/components/ui";
import { forgotSchema } from "@/schemas/auth";
import { authApi } from "@/services/auth";
import { AuthLayout, DevLink, FormError } from "./AuthLayout";

type V = z.infer<typeof forgotSchema>;
export function ForgotPasswordPage() {
  const f = useForm<V>({ resolver: zodResolver(forgotSchema) });
  const m = useMutation({ mutationFn: (v: V) => authApi.forgot(v.email) });
  return (
    <AuthLayout title="Reset your password" subtitle="We’ll email you a link to choose a new one.">
      <form className="space-y-4" onSubmit={f.handleSubmit((v) => m.mutate(v))} noValidate>
        <Input label="Email" type="email" error={f.formState.errors.email?.message} {...f.register("email")} />
        <FormError message={m.error?.message} />
        {m.data && <p className="text-sm text-ok">{m.data.message}</p>}
        <DevLink link={m.data?.dev_link} />
        <Button type="submit" className="w-full" disabled={m.isPending}>{m.isPending ? "Sending…" : "Send reset link"}</Button>
      </form>
      <Link className="text-sm text-electric underline" to="/signin">Back to sign in</Link>
    </AuthLayout>
  );
}
