// frontend/src/features/auth/AuthGuard.tsx
'use client';

import { useEffect } from 'react';

import { useRouter } from '@/i18n/routing';
import { useAuthStore } from '@/stores/auth-store';

import { useCurrentUser } from './use-auth';

/** Redirects to /login if there's no authenticated session once hydration completes. */
export function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { isLoading } = useCurrentUser();
  const isHydrated = useAuthStore((s) => s.isHydrated);
  const user = useAuthStore((s) => s.user);

  useEffect(() => {
    if (isHydrated && !user) {
      router.replace('/login');
    }
  }, [isHydrated, user, router]);

  if (!isHydrated || isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    );
  }

  if (!user) return null;

  return <>{children}</>;
}
