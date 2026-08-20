// frontend/src/features/auth/RegisterForm.tsx
'use client';

import { zodResolver } from '@hookform/resolvers/zod';
import { useTranslations } from 'next-intl';
import { useState } from 'react';
import { useForm } from 'react-hook-form';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { ApiClientError } from '@/lib/api-client';
import { Link, useRouter } from '@/i18n/routing';

import { useRegister } from './use-auth';
import { registerSchema, type RegisterFormValues } from './schemas';

export function RegisterForm() {
  const t = useTranslations('auth');
  const router = useRouter();
  const registerMutation = useRegister();
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<RegisterFormValues>({ resolver: zodResolver(registerSchema) });

  const onSubmit = async (values: RegisterFormValues) => {
    setServerError(null);
    try {
      await registerMutation.mutateAsync(values);
      router.push('/dashboard');
    } catch (err) {
      if (err instanceof ApiClientError && err.code === 'email_taken') {
        setServerError(t('emailTaken'));
      } else {
        setServerError(t('genericError'));
      }
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
      <div className="space-y-2">
        <Label htmlFor="company_name">{t('companyName')}</Label>
        <Input id="company_name" {...register('company_name')} aria-invalid={!!errors.company_name} />
        {errors.company_name && <p className="text-sm text-destructive">{errors.company_name.message}</p>}
      </div>

      <div className="space-y-2">
        <Label htmlFor="full_name">{t('fullName')}</Label>
        <Input id="full_name" {...register('full_name')} aria-invalid={!!errors.full_name} />
        {errors.full_name && <p className="text-sm text-destructive">{errors.full_name.message}</p>}
      </div>

      <div className="space-y-2">
        <Label htmlFor="email">{t('email')}</Label>
        <Input id="email" type="email" autoComplete="email" {...register('email')} aria-invalid={!!errors.email} />
        {errors.email && <p className="text-sm text-destructive">{errors.email.message}</p>}
      </div>

      <div className="space-y-2">
        <Label htmlFor="password">{t('password')}</Label>
        <Input
          id="password"
          type="password"
          autoComplete="new-password"
          {...register('password')}
          aria-invalid={!!errors.password}
        />
        {errors.password && <p className="text-sm text-destructive">{errors.password.message}</p>}
      </div>

      {serverError && (
        <p role="alert" className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">
          {serverError}
        </p>
      )}

      <Button type="submit" className="w-full" disabled={isSubmitting}>
        {t('registerButton')}
      </Button>

      <p className="text-center text-sm text-muted-foreground">
        {t('haveAccount')}{' '}
        <Link href="/login" className="font-medium text-primary hover:underline">
          {t('signInLink')}
        </Link>
      </p>
    </form>
  );
}
