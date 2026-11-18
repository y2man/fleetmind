import { z } from "zod";

export const password = z.string().min(10, "At least 10 characters").regex(/[A-Za-z]/, "Include a letter").regex(/\d/, "Include a number");
const email = z.string().email("Enter a valid email");

export const signInSchema = z.object({ email, password: z.string().min(1, "Enter your password") });
export const signUpSchema = z.object({
  full_name: z.string().min(1, "Required"), organization_name: z.string().min(1, "Required"), email, password, confirm: z.string(),
}).refine((v) => v.password === v.confirm, { path: ["confirm"], message: "Passwords don’t match" });
export const forgotSchema = z.object({ email });
export const resetSchema = z.object({ new_password: password, confirm: z.string() }).refine((v) => v.new_password === v.confirm, { path: ["confirm"], message: "Passwords don’t match" });
export const profileSchema = z.object({ full_name: z.string().min(1, "Required"), phone: z.string().max(40).optional() });
export const orgSchema = z.object({ name: z.string().min(1, "Required"), country: z.string().max(80).optional(), timezone: z.string().max(64).optional(), fleet_size: z.coerce.number().int().min(0).max(100000).optional() });
export const inviteSchema = z.object({ email, full_name: z.string().min(1, "Required"), role: z.enum(["admin", "dispatcher", "viewer"]) });

export type SignUpValues = z.infer<typeof signUpSchema>;
export type OrgValues = z.infer<typeof orgSchema>;
