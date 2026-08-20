// frontend/src/app/[locale]/(app)/reports/page.tsx
'use client';

import { Download, FileSpreadsheet, FileText, Loader2 } from 'lucide-react';
import { useState } from 'react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { DatasetPicker } from '@/components/shared/DatasetPicker';
import { EmptyState } from '@/components/shared/EmptyState';
import { downloadReport, useGenerateReport } from '@/features/reports/use-reports';
import { ApiClientError } from '@/lib/api-client';
import type { ReportFormat } from '@/types/api';

function ReportOption({
  icon: Icon, title, description, format, datasetId,
}: {
  icon: typeof FileText; title: string; description: string; format: ReportFormat; datasetId: string;
}) {
  const generate = useGenerateReport();
  const [downloading, setDownloading] = useState(false);

  const handleGenerate = async () => {
    const report = await generate.mutateAsync({ dataset_id: datasetId, format });
    setDownloading(true);
    try {
      await downloadReport(report);
    } finally {
      setDownloading(false);
    }
  };

  const isBusy = generate.isPending || downloading;

  return (
    <Card>
      <CardHeader>
        <Icon className="mb-2 h-6 w-6 text-primary" />
        <CardTitle>{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-2">
        <Button onClick={handleGenerate} disabled={!datasetId || isBusy} className="w-full">
          {isBusy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
          Generer et telecharger
        </Button>
        {generate.isError && (
          <p className="text-sm text-destructive">
            {generate.error instanceof ApiClientError ? generate.error.message : 'Une erreur est survenue.'}
          </p>
        )}
      </CardContent>
    </Card>
  );
}

export default function ReportsPage() {
  const [datasetId, setDatasetId] = useState('');

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Rapports</h1>
        <p className="text-muted-foreground">Generez un rapport executif PDF ou un classeur Excel complet a partir des dernieres analyses.</p>
      </div>

      <DatasetPicker value={datasetId} onChange={setDatasetId} />

      {!datasetId ? (
        <EmptyState icon={FileText} title="Choisissez un jeu de donnees" description="Selectionnez un jeu de donnees pour generer un rapport." />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2">
          <ReportOption
            icon={FileText}
            title="Rapport executif (PDF)"
            description="Synthese des KPI, verdicts de validation du modele, graphique de prevision et top 5 des recommandations."
            format="pdf"
            datasetId={datasetId}
          />
          <ReportOption
            icon={FileSpreadsheet}
            title="Resultats bruts (Excel)"
            description="Classeur complet : une feuille par analyse (descriptif, regression, validation, prevision, segments, KPI, decisions)."
            format="xlsx"
            datasetId={datasetId}
          />
        </div>
      )}
    </div>
  );
}
