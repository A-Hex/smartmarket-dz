// frontend/src/features/auth/schemas.ts
import { z } from 'zod';

export const loginSchema = z.object({
  email: z.string().email(),
  password: z.string().min(1),
});
export type LoginFormValues = z.infer<typeof loginSchema>;

export const registerSchema = z.object({
  company_name: z.string().min(2).max(255),
  full_name: z.string().min(2).max(255),
  email: z.string().email(),
  password: z.string().min(8).max(128),
});
export type RegisterFormValues = z.infer<typeof registerSchema>;
