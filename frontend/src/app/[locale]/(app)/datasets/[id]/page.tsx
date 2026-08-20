// frontend/src/app/[locale]/(app)/datasets/[id]/page.tsx
'use client';

import { useLocale, useTranslations } from 'next-intl';
import { useState } from 'react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { useDataset, useDatasetPreview, useDeleteDataset } from '@/features/datasets/use-datasets';
import { useRouter } from '@/i18n/routing';
import { formatDate, formatNumber } from '@/lib/utils';

export default function DatasetDetailPage({ params }: { params: { id: string } }) {
  const t = useTranslations('datasets');
  const locale = useLocale();
  const router = useRouter();
  const { data: dataset, isLoading } = useDataset(params.id);
  const { data: preview, isLoading: previewLoading } = useDatasetPreview(params.id, 20);
  const deleteDataset = useDeleteDataset();
  const [showColumns, setShowColumns] = useState(true);

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }

  if (!dataset) return <p className="text-muted-foreground">Jeu de donnees introuvable.</p>;

  const handleDelete = async () => {
    if (!confirm('Supprimer ce jeu de donnees ? Cette action est definitive.')) return;
    await deleteDataset.mutateAsync(dataset.id);
    router.push('/datasets');
  };

  return (
    <div className="space-y-8">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">{dataset.name}</h1>
          <p className="text-sm text-muted-foreground">
            {formatNumber(dataset.row_count ?? 0, locale)} {t('rows')} - {dataset.column_count} {t('columns')} -{' '}
            {formatDate(dataset.created_at, locale)}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge>{t(`status.${dataset.status}`)}</Badge>
          <Button variant="outline" size="sm" onClick={() => router.push(`/cleaning?dataset=${dataset.id}`)}>
            Nettoyer
          </Button>
          <Button variant="outline" size="sm" onClick={() => router.push(`/analytics?dataset=${dataset.id}`)}>
            Analyser
          </Button>
          <Button variant="destructive" size="sm" onClick={handleDelete} disabled={deleteDataset.isPending}>
            Supprimer
          </Button>
        </div>
      </div>

      <section>
        <button
          className="mb-3 text-sm font-medium text-primary hover:underline"
          onClick={() => setShowColumns((v) => !v)}
        >
          {showColumns ? 'Masquer' : 'Afficher'} le profil des colonnes ({dataset.columns.length})
        </button>
        {showColumns && (
          <div className="overflow-x-auto rounded-lg border border-border">
            <table className="w-full text-sm">
              <thead className="bg-secondary text-secondary-foreground">
                <tr>
                  {['Colonne', 'Type', 'Manquants', 'Uniques', 'Min', 'Max', 'Moyenne', 'Cible ?'].map((h) => (
                    <th key={h} className="px-3 py-2 text-start font-medium">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {dataset.columns.map((col) => (
                  <tr key={col.id} className="border-t border-border">
                    <td className="px-3 py-2 font-medium">{col.name}</td>
                    <td className="px-3 py-2 font-mono-data text-muted-foreground">{col.dtype}</td>
                    <td className="px-3 py-2 font-mono-data">{col.null_count}</td>
                    <td className="px-3 py-2 font-mono-data">{col.unique_count}</td>
                    <td className="px-3 py-2 font-mono-data">{col.min_value?.toFixed(2) ?? '-'}</td>
                    <td className="px-3 py-2 font-mono-data">{col.max_value?.toFixed(2) ?? '-'}</td>
                    <td className="px-3 py-2 font-mono-data">{col.mean_value?.toFixed(2) ?? '-'}</td>
                    <td className="px-3 py-2">
                      {col.is_target_candidate && <Badge variant="success">Candidat</Badge>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section>
        <h2 className="mb-3 text-lg font-semibold">Apercu des donnees</h2>
        {previewLoading ? (
          <Skeleton className="h-64 w-full" />
        ) : preview ? (
          <div className="overflow-x-auto rounded-lg border border-border">
            <table className="w-full text-sm">
              <thead className="bg-secondary text-secondary-foreground">
                <tr>
                  {preview.columns.map((col) => (
                    <th key={col} className="px-3 py-2 text-start font-medium">
                      {col}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {preview.rows.map((row, i) => (
                  <tr key={i} className="border-t border-border">
                    {preview.columns.map((col) => (
                      <td key={col} className="px-3 py-2 font-mono-data">
                        {row[col] === null || row[col] === undefined ? '-' : String(row[col])}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
        {preview && (
          <p className="mt-2 text-xs text-muted-foreground">
            Affichage de {preview.preview_rows} sur {formatNumber(preview.total_rows, locale)} lignes.
          </p>
        )}
      </section>
    </div>
  );
}
