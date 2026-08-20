// frontend/src/app/[locale]/(app)/cleaning/page.tsx
'use client';

import { Loader2, SprayCan } from 'lucide-react';
import { useState } from 'react';

import { Button } from '@/components/ui/button';
import { DatasetPicker } from '@/components/shared/DatasetPicker';
import { EmptyState } from '@/components/shared/EmptyState';
import { CleaningReportView } from '@/features/cleaning/CleaningReportView';
import { ColumnConfigRow } from '@/features/cleaning/ColumnConfigRow';
import { useRunCleaning, type ColumnCleaningConfig } from '@/features/cleaning/use-cleaning';
import { useDataset } from '@/features/datasets/use-datasets';
import { ApiClientError } from '@/lib/api-client';

function defaultConfig(columnName: string): ColumnCleaningConfig {
  return { column: columnName, missing_strategy: 'none', outlier_method: 'none', outlier_action: 'none' };
}

export default function CleaningPage() {
  const [datasetId, setDatasetId] = useState('');
  const { data: dataset } = useDataset(datasetId || undefined);
  const [configs, setConfigs] = useState<Record<string, ColumnCleaningConfig>>({});
  const runCleaning = useRunCleaning(datasetId);

  const handleSelectDataset = (id: string) => {
    setDatasetId(id);
    setConfigs({});
  };

  const getConfig = (columnName: string): ColumnCleaningConfig => configs[columnName] ?? defaultConfig(columnName);

  const updateConfig = (columnName: string, next: ColumnCleaningConfig) => {
    setConfigs((prev) => ({ ...prev, [columnName]: next }));
  };

  const handleRun = () => {
    if (!dataset) return;
    const columns = dataset.columns.map((c) => getConfig(c.name));
    runCleaning.mutate(columns);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Nettoyage des donnees</h1>
        <p className="text-muted-foreground">
          Configurez une strategie par colonne pour les valeurs manquantes et les valeurs aberrantes, puis lancez le nettoyage.
        </p>
      </div>

      <DatasetPicker value={datasetId} onChange={handleSelectDataset} />

      {!datasetId || !dataset ? (
        <EmptyState icon={SprayCan} title="Choisissez un jeu de donnees" description="Selectionnez un jeu de donnees a nettoyer." />
      ) : (
        <div className="space-y-6">
          <div className="overflow-x-auto rounded-lg border border-border">
            <table className="w-full text-sm">
              <thead className="bg-secondary text-secondary-foreground">
                <tr>
                  {['Colonne', 'Valeurs manquantes', 'Methode de detection', 'Action sur les aberrantes'].map((h) => (
                    <th key={h} className="px-3 py-2 text-start font-medium">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {dataset.columns.map((col) => (
                  <ColumnConfigRow
                    key={col.id}
                    column={col}
                    config={getConfig(col.name)}
                    onChange={(next) => updateConfig(col.name, next)}
                  />
                ))}
              </tbody>
            </table>
          </div>

          <Button onClick={handleRun} disabled={runCleaning.isPending}>
            {runCleaning.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
            Lancer le nettoyage
          </Button>

          {runCleaning.isError && (
            <p className="text-sm text-destructive">
              {runCleaning.error instanceof ApiClientError ? runCleaning.error.message : 'Une erreur est survenue.'}
            </p>
          )}

          {runCleaning.data?.report && <CleaningReportView report={runCleaning.data.report} />}
        </div>
      )}
    </div>
  );
}
