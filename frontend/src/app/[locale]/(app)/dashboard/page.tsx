// frontend/src/app/[locale]/(app)/dashboard/page.tsx
'use client';

import { ArrowRight, Database } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { useDatasets } from '@/features/datasets/use-datasets';
import { Link } from '@/i18n/routing';
import { useAuthStore } from '@/stores/auth-store';

export default function DashboardPage() {
  const { data: datasets, isLoading } = useDatasets();
  const company = useAuthStore((s) => s.company);

  const analyzed = datasets?.filter((d) => d.status === 'analyzed').length ?? 0;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold">Bonjour{company ? `, ${company.name}` : ''}</h1>
        <p className="text-muted-foreground">Voici un apercu de votre activite.</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Jeux de donnees</CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? <Skeleton className="h-8 w-16" /> : <p className="font-mono-data text-3xl font-semibold">{datasets?.length ?? 0}</p>}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Analyses</CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? <Skeleton className="h-8 w-16" /> : <p className="font-mono-data text-3xl font-semibold">{analyzed}</p>}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Decisions ouvertes</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="font-mono-data text-3xl font-semibold text-muted-foreground">-</p>
          </CardContent>
        </Card>
      </div>

      {!isLoading && (!datasets || datasets.length === 0) && (
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-12 text-center">
            <Database className="h-8 w-8 text-muted-foreground" strokeWidth={1.5} />
            <p className="text-muted-foreground">
              Importez votre premier jeu de donnees pour commencer a generer des analyses et des recommandations.
            </p>
            <Button asChild>
              <Link href="/datasets">
                Importer un fichier <ArrowRight className="ms-1 h-4 w-4" />
              </Link>
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
