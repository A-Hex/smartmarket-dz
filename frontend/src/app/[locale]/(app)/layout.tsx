// frontend/src/app/[locale]/(app)/layout.tsx
import { AuthGuard } from '@/features/auth/AuthGuard';
import { AppShell } from '@/features/dashboard/AppShell';

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthGuard>
      <AppShell>{children}</AppShell>
    </AuthGuard>
  );
}
