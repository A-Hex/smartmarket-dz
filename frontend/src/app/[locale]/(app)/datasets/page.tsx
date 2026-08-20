// frontend/src/app/[locale]/(app)/datasets/page.tsx
'use client';

import { Database, FileSpreadsheet } from 'lucide-react';
import { useLocale, useTranslations } from 'next-intl';

import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { DatasetUpload } from '@/features/datasets/DatasetUpload';
import { useDatasets } from '@/features/datasets/use-datasets';
import { Link } from '@/i18n/routing';
import { formatDate } from '@/lib/utils';

const STATUS_VARIANT: Record<string, 'secondary' | 'warning' | 'success' | 'destructive'> = {
  uploaded: 'secondary',
  cleaning: 'warning',
  cleaned: 'success',
  analyzed: 'success',
  failed: 'destructive',
};

export default function DatasetsPage() {
  const t = useTranslations('datasets');
  const locale = useLocale();
  const { data: datasets, isLoading } = useDatasets();

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold">{t('title')}</h1>
      </div>

      <DatasetUpload />

      {isLoading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-20 w-full" />
          ))}
        </div>
      ) : datasets && datasets.length > 0 ? (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {datasets.map((dataset) => (
            <Link
              key={dataset.id}
              href={`/datasets/${dataset.id}`}
              className="flex flex-col gap-2 rounded-lg border border-border bg-card p-5 transition-colors hover:border-primary/40"
            >
              <div className="flex items-start justify-between gap-2">
                <FileSpreadsheet className="h-5 w-5 shrink-0 text-primary" strokeWidth={1.75} />
                <Badge variant={STATUS_VARIANT[dataset.status] ?? 'secondary'}>
                  {t(`status.${dataset.status}`)}
                </Badge>
              </div>
              <p className="truncate font-medium">{dataset.name}</p>
              <p className="text-sm text-muted-foreground">
                {dataset.row_count ?? '—'} {t('rows')} · {dataset.column_count ?? '—'} {t('columns')}
              </p>
              <p className="text-xs text-muted-foreground">{formatDate(dataset.created_at, locale)}</p>
            </Link>
          ))}
        </div>
      ) : (
        <div className="flex flex-col items-center gap-2 rounded-lg border border-dashed border-border py-16 text-center">
          <Database className="h-8 w-8 text-muted-foreground" strokeWidth={1.5} />
          <p className="text-muted-foreground">{t('empty')}</p>
        </div>
      )}
    </div>
  );
}
