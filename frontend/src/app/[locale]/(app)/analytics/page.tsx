// frontend/src/app/[locale]/(app)/analytics/page.tsx
'use client';

import { BarChart3 } from 'lucide-react';
import { useState } from 'react';

import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { DatasetPicker } from '@/components/shared/DatasetPicker';
import { EmptyState } from '@/components/shared/EmptyState';
import { ANOVATab } from '@/features/analytics/ANOVATab';
import { DescriptiveTab } from '@/features/analytics/DescriptiveTab';
import { ForecastTab } from '@/features/analytics/ForecastTab';
import { RegressionTab } from '@/features/analytics/RegressionTab';
import { SegmentationTab } from '@/features/analytics/SegmentationTab';
import { ValidationTab } from '@/features/analytics/ValidationTab';
import { useDataset } from '@/features/datasets/use-datasets';

export default function AnalyticsPage() {
  const [datasetId, setDatasetId] = useState('');
  const [modelId, setModelId] = useState<string | null>(null);
  const { data: dataset } = useDataset(datasetId || undefined);
  const columns = dataset?.columns.map((c) => c.name) ?? [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Analyses</h1>
        <p className="text-muted-foreground">Statistiques descriptives, regression, ANOVA, validation, prevision et segmentation.</p>
      </div>

      <DatasetPicker value={datasetId} onChange={(id) => { setDatasetId(id); setModelId(null); }} />

      {!datasetId ? (
        <EmptyState
          icon={BarChart3}
          title="Choisissez un jeu de donnees"
          description="Selectionnez un jeu de donnees ci-dessus pour lancer une analyse."
        />
      ) : (
        <Tabs defaultValue="descriptive">
          <TabsList>
            <TabsTrigger value="descriptive">Descriptif</TabsTrigger>
            <TabsTrigger value="regression">Regression</TabsTrigger>
            <TabsTrigger value="anova">ANOVA</TabsTrigger>
            <TabsTrigger value="validation">Validation</TabsTrigger>
            <TabsTrigger value="forecast">Prevision</TabsTrigger>
            <TabsTrigger value="segmentation">Segmentation</TabsTrigger>
          </TabsList>

          <TabsContent value="descriptive"><DescriptiveTab datasetId={datasetId} /></TabsContent>
          <TabsContent value="regression">
            <RegressionTab datasetId={datasetId} columns={columns} onModelFitted={setModelId} />
          </TabsContent>
          <TabsContent value="anova"><ANOVATab datasetId={datasetId} columns={columns} /></TabsContent>
          <TabsContent value="validation"><ValidationTab modelId={modelId} /></TabsContent>
          <TabsContent value="forecast"><ForecastTab datasetId={datasetId} columns={columns} /></TabsContent>
          <TabsContent value="segmentation"><SegmentationTab datasetId={datasetId} columns={columns} /></TabsContent>
        </Tabs>
      )}
    </div>
  );
}
