// frontend/src/features/kpis/KPIGrid.tsx
'use client';

import { TrendingDown, TrendingUp } from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import type { KPIItem, KPISuiteResult } from '@/types/api';

const KPI_LABELS: Record<string, string> = {
  cltv: 'CLTV',
  churn: 'Taux de churn',
  take_rate: 'Take rate',
  cac: "Cout d'acquisition (CAC)",
  wom: 'Bouche-a-oreille (WOM)',
  revenue_growth: 'Croissance du revenu',
  gross_margin: 'Marge brute',
};

function KPICard({ item }: { item: KPIItem }) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          {KPI_LABELS[item.kpi_type] ?? item.kpi_type}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {item.status === 'computed' && item.value !== null ? (
          <>
            <div className="flex items-baseline gap-2">
              <p className="font-mono-data text-2xl font-semibold">{item.value.toFixed(2)}</p>
              {item.trend && item.trend.direction !== 'flat' && (
                <span className={item.trend.direction === 'up' ? 'text-success' : 'text-destructive'}>
                  {item.trend.direction === 'up' ? <TrendingUp className="h-4 w-4" /> : <TrendingDown className="h-4 w-4" />}
                </span>
              )}
            </div>
            <p className="mt-1 text-xs text-muted-foreground">{item.formula}</p>
            <p className="mt-2 text-xs">{item.interpretation}</p>
          </>
        ) : (
          <>
            <Badge variant="secondary">Donnees insuffisantes</Badge>
            <p className="mt-2 text-xs text-muted-foreground">
              Colonnes manquantes : {item.missing.join(', ')}
            </p>
          </>
        )}
      </CardContent>
    </Card>
  );
}

export function KPIGrid({ result }: { result: KPISuiteResult }) {
  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {result.kpis.map((item) => <KPICard key={item.kpi_type} item={item} />)}
      </div>

      <div>
        <h3 className="mb-2 text-sm font-semibold">Indicateurs complementaires</h3>
        <div className="grid gap-3 sm:grid-cols-2">
          {result.supporting_metrics.map((m) => (
            <div key={m.name} className="rounded-lg border border-border p-3">
              <p className="text-xs text-muted-foreground">{m.name.replace(/_/g, ' ')}</p>
              <p className="font-mono-data text-lg font-semibold">
                {m.status === 'computed' && m.value !== null ? m.value.toFixed(2) : '—'}
              </p>
              <p className="text-xs text-muted-foreground">{m.formula}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
