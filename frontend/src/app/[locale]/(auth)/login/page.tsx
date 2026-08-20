// frontend/src/app/[locale]/(auth)/login/page.tsx
import { useTranslations } from 'next-intl';

import { LoginForm } from '@/features/auth/LoginForm';

export default function LoginPage() {
  const t = useTranslations('auth');
  return (
    <div className="space-y-6">
      <h1 className="text-center text-2xl font-semibold">{t('loginTitle')}</h1>
      <LoginForm />
    </div>
  );
}
