// frontend/src/app/[locale]/page.tsx
import { BarChart3, Brain, ShieldCheck } from 'lucide-react';
import { useTranslations } from 'next-intl';

import { Button } from '@/components/ui/button';
import { Link } from '@/i18n/routing';

export default function LandingPage() {
  const t = useTranslations('landing');

  return (
    <main className="flex min-h-screen flex-col">
      <header className="border-b border-border">
        <div className="container flex h-16 items-center justify-between">
          <span className="font-display text-xl font-semibold text-primary">{t('title')}</span>
          <Button asChild variant="ghost">
            <Link href="/login">{t('login')}</Link>
          </Button>
        </div>
      </header>

      <section className="container flex flex-1 flex-col items-center justify-center gap-8 py-24 text-center">
        <div className="inline-flex items-center gap-2 rounded-full border border-accent/40 bg-accent/10 px-4 py-1.5 text-sm font-medium text-accent-foreground">
          <span className="h-1.5 w-1.5 rounded-full bg-accent" />
          Data → Décision → Action
        </div>

        <h1 className="max-w-3xl font-display text-4xl font-semibold leading-tight text-foreground sm:text-6xl">
          {t('subtitle')}
        </h1>

        <p className="max-w-xl text-lg text-muted-foreground">{t('description')}</p>

        <Button asChild size="lg" className="mt-2">
          <Link href="/register">{t('cta')}</Link>
        </Button>

        <div className="mt-16 grid gap-8 sm:grid-cols-3">
          {[
            { icon: BarChart3, label: 'Analyses statistiques rigoureuses' },
            { icon: ShieldCheck, label: 'Validation de modèle systématique' },
            { icon: Brain, label: "Moteur de décision automatisé" },
          ].map(({ icon: Icon, label }) => (
            <div key={label} className="flex flex-col items-center gap-3 rounded-lg border border-border bg-card p-6">
              <Icon className="h-6 w-6 text-primary" strokeWidth={1.75} />
              <p className="text-sm text-card-foreground">{label}</p>
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}
