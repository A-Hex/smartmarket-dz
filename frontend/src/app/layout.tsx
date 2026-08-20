// frontend/src/app/layout.tsx
import type { Metadata } from 'next';

import './globals.css';

export const metadata: Metadata = {
  title: 'SmartMarket DZ',
  description: "Plateforme d'aide à la décision pour le marché algérien",
};

// Root layout is a thin pass-through; [locale]/layout.tsx owns <html>/<body>
// since it needs the resolved locale for lang/dir attributes.
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return children;
}
