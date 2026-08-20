// frontend/src/app/[locale]/(auth)/layout.tsx
import { useTranslations } from 'next-intl';

import { Link } from '@/i18n/routing';

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  const t = useTranslations('landing');

  return (
    <div className="flex min-h-screen items-center justify-center bg-secondary/30 px-4">
      <div className="w-full max-w-sm space-y-6">
        <Link href="/" className="block text-center font-display text-2xl font-semibold text-primary">
          {t('title')}
        </Link>
        <div className="rounded-lg border border-border bg-card p-6 shadow-sm">{children}</div>
      </div>
    </div>
  );
}
