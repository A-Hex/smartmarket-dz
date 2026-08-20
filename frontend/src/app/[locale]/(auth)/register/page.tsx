// frontend/src/app/[locale]/(auth)/register/page.tsx
import { useTranslations } from 'next-intl';

import { RegisterForm } from '@/features/auth/RegisterForm';

export default function RegisterPage() {
  const t = useTranslations('auth');
  return (
    <div className="space-y-6">
      <h1 className="text-center text-2xl font-semibold">{t('registerTitle')}</h1>
      <RegisterForm />
    </div>
  );
}
