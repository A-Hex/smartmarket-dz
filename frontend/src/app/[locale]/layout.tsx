// frontend/src/app/[locale]/layout.tsx
import { Fraunces, Inter, JetBrains_Mono } from 'next/font/google';
import { NextIntlClientProvider } from 'next-intl';
import { getMessages } from 'next-intl/server';
import { notFound } from 'next/navigation';
import type { Metadata } from 'next';

import { QueryProvider } from '@/components/shared/query-provider';
import { routing } from '@/i18n/routing';

import '../globals.css';

const fraunces = Fraunces({ subsets: ['latin'], variable: '--font-display-sans', display: 'swap' });
const inter = Inter({ subsets: ['latin'], variable: '--font-body-sans', display: 'swap' });
const jetbrainsMono = JetBrains_Mono({ subsets: ['latin'], variable: '--font-mono-sans', display: 'swap' });

export const metadata: Metadata = {
  title: 'SmartMarket DZ',
  description: "Plateforme d'aide à la décision pour le marché algérien",
};

export function generateStaticParams() {
  return routing.locales.map((locale) => ({ locale }));
}

export default async function LocaleLayout({
  children,
  params: { locale },
}: {
  children: React.ReactNode;
  params: { locale: string };
}) {
  if (!routing.locales.includes(locale as (typeof routing.locales)[number])) {
    notFound();
  }

  const messages = await getMessages();
  const dir = locale === 'ar' ? 'rtl' : 'ltr';

  return (
    <html lang={locale} dir={dir} className={`${fraunces.variable} ${inter.variable} ${jetbrainsMono.variable}`}>
      <body>
        <NextIntlClientProvider messages={messages}>
          <QueryProvider>{children}</QueryProvider>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
