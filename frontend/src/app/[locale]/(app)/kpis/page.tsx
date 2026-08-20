// frontend/src/app/[locale]/(app)/kpis/page.tsx
'use client';

import { Gauge } from 'lucide-react';
import { useState } from 'react';

import { DatasetPicker } from '@/components/shared/DatasetPicker';
import { EmptyState } from '@/components/shared/EmptyState';
import { useRunKpis } from '@/features/analytics/use-analytics';
import { useDataset } from '@/features/datasets/use-datasets';
import { KPIConfigForm, type KPIConfigValues } from '@/features/kpis/KPIConfigForm';
import { KPIGrid } from '@/features/kpis/KPIGrid';
import { ApiClientError } from '@/lib/api-client';

export default function KPIsPage() {
  const [datasetId, setDatasetId] = useState('');
  const { data: dataset } = useDataset(datasetId || undefined);
  const columns = dataset?.columns.map((c) => c.name) ?? [];
  const runKpis = useRunKpis();

  const handleSubmit = (values: KPIConfigValues) => {
    runKpis.mutate({ dataset_id: datasetId, ...values });
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">KPI</h1>
        <p className="text-muted-foreground">CLTV, churn, take rate, CAC, WOM, croissance et marge, avec formules et couverture des donnees.</p>
      </div>

      <DatasetPicker value={datasetId} onChange={setDatasetId} />

      {!datasetId ? (
        <EmptyState icon={Gauge} title="Choisissez un jeu de donnees" description="Selectionnez un jeu de donnees pour calculer ses KPI." />
      ) : (
        <div className="space-y-6">
          <KPIConfigForm columns={columns} onSubmit={handleSubmit} isPending={runKpis.isPending} />

          {runKpis.isError && (
            <p className="text-sm text-destructive">
              {runKpis.error instanceof ApiClientError ? runKpis.error.message : 'Une erreur est survenue.'}
            </p>
          )}

          {runKpis.data && <KPIGrid result={runKpis.data} />}
        </div>
      )}
    </div>
  );
}
