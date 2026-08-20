// frontend/src/features/dashboard/AppShell.tsx
'use client';

import {
  BarChart3,
  Database,
  LayoutDashboard,
  LineChart,
  ListChecks,
  LogOut,
  Menu,
  Settings,
  Sparkles,
  Wand2,
} from 'lucide-react';
import { useTranslations } from 'next-intl';
import { useState } from 'react';

import { Button } from '@/components/ui/button';
import { Sheet, SheetContent, SheetTrigger } from '@/components/ui/sheet';
import { useLogout } from '@/features/auth/use-auth';
import { Link, usePathname } from '@/i18n/routing';
import { useAuthStore } from '@/stores/auth-store';
import { cn } from '@/lib/utils';

const NAV_ITEMS = [
  { href: '/dashboard', key: 'dashboard', icon: LayoutDashboard },
  { href: '/datasets', key: 'datasets', icon: Database },
  { href: '/cleaning', key: 'cleaning', icon: Wand2 },
  { href: '/analytics', key: 'analytics', icon: LineChart },
  { href: '/kpis', key: 'kpis', icon: BarChart3 },
  { href: '/decisions', key: 'decisions', icon: Sparkles },
  { href: '/reports', key: 'reports', icon: ListChecks },
  { href: '/settings', key: 'settings', icon: Settings },
] as const;

function NavLinks({ pathname, t, onNavigate }: { pathname: string; t: (k: string) => string; onNavigate?: () => void }) {
  return (
    <nav className="flex-1 space-y-1 p-3">
      {NAV_ITEMS.map(({ href, key, icon: Icon }) => {
        const active = pathname === href || pathname.startsWith(`${href}/`);
        return (
          <Link
            key={href}
            href={href}
            onClick={onNavigate}
            className={cn(
              'flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors',
              active
                ? 'bg-primary text-primary-foreground'
                : 'text-muted-foreground hover:bg-secondary hover:text-secondary-foreground'
            )}
          >
            <Icon className="h-4 w-4" strokeWidth={1.75} />
            {t(key)}
          </Link>
        );
      })}
    </nav>
  );
}

function SidebarFooter({ t, onLogout }: { t: (k: string) => string; onLogout: () => void }) {
  const company = useAuthStore((s) => s.company);
  const user = useAuthStore((s) => s.user);

  return (
    <div className="border-t border-border p-3">
      <div className="mb-2 px-3">
        <p className="truncate text-sm font-medium">{user?.full_name}</p>
        <p className="truncate text-xs text-muted-foreground">{company?.name}</p>
      </div>
      <Button variant="ghost" size="sm" className="w-full justify-start gap-2" onClick={onLogout}>
        <LogOut className="h-4 w-4" strokeWidth={1.75} />
        {t('logout')}
      </Button>
    </div>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const t = useTranslations('nav');
  const pathname = usePathname();
  const logout = useLogout();
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  return (
    <div className="flex min-h-screen flex-col md:flex-row">
      {/* Mobile top bar: brand + menu trigger. Below md, this replaces the sidebar entirely. */}
      <header className="flex h-14 items-center justify-between border-b border-border bg-card px-4 md:hidden">
        <Link href="/dashboard" className="font-display text-base font-semibold text-primary">
          SmartMarket DZ
        </Link>
        <Sheet open={mobileNavOpen} onOpenChange={setMobileNavOpen}>
          <SheetTrigger asChild>
            <Button variant="ghost" size="icon" aria-label={t('dashboard')}>
              <Menu className="h-5 w-5" />
            </Button>
          </SheetTrigger>
          <SheetContent className="flex flex-col">
            <div className="flex h-14 items-center border-b border-border px-4">
              <span className="font-display text-base font-semibold text-primary">SmartMarket DZ</span>
            </div>
            <NavLinks pathname={pathname} t={t} onNavigate={() => setMobileNavOpen(false)} />
            <SidebarFooter t={t} onLogout={logout} />
          </SheetContent>
        </Sheet>
      </header>

      {/* Desktop sidebar */}
      <aside className="hidden w-64 flex-col border-e border-border bg-card md:flex">
        <div className="flex h-16 items-center border-b border-border px-6">
          <Link href="/dashboard" className="font-display text-lg font-semibold text-primary">
            SmartMarket DZ
          </Link>
        </div>
        <NavLinks pathname={pathname} t={t} />
        <SidebarFooter t={t} onLogout={logout} />
      </aside>

      <div className="flex flex-1 flex-col">
        <main className="flex-1 p-4 md:p-8">{children}</main>
      </div>
    </div>
  );
}
