// frontend/src/features/datasets/DatasetUpload.tsx
'use client';

import { Loader2, UploadCloud } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { useRef, useState } from 'react';

import { ApiClientError } from '@/lib/api-client';
import { cn } from '@/lib/utils';
import { useRouter } from '@/i18n/routing';

import { useUploadDataset } from './use-datasets';

const ACCEPTED_EXTENSIONS = ['.csv', '.xlsx', '.xls'];

export function DatasetUpload() {
  const t = useTranslations('datasets');
  const router = useRouter();
  const upload = useUploadDataset();
  const inputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFile = async (file: File) => {
    setError(null);
    const ext = file.name.slice(file.name.lastIndexOf('.')).toLowerCase();
    if (!ACCEPTED_EXTENSIONS.includes(ext)) {
      setError('Seuls les fichiers CSV et Excel (.csv, .xlsx, .xls) sont acceptés.');
      return;
    }
    try {
      const dataset = await upload.mutateAsync(file);
      router.push(`/datasets/${dataset.id}`);
    } catch (err) {
      setError(err instanceof ApiClientError ? err.message : 'Le téléversement a échoué.');
    }
  };

  return (
    <div>
      <div
        role="button"
        tabIndex={0}
        onClick={() => inputRef.current?.click()}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') inputRef.current?.click();
        }}
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setIsDragging(false);
          const file = e.dataTransfer.files?.[0];
          if (file) handleFile(file);
        }}
        className={cn(
          'flex cursor-pointer flex-col items-center justify-center gap-3 rounded-lg border-2 border-dashed p-12 text-center transition-colors',
          isDragging ? 'border-primary bg-primary/5' : 'border-border hover:border-primary/50'
        )}
      >
        {upload.isPending ? (
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        ) : (
          <UploadCloud className="h-8 w-8 text-muted-foreground" strokeWidth={1.5} />
        )}
        <div>
          <p className="font-medium">{t('upload')}</p>
          <p className="text-sm text-muted-foreground">{t('uploadHint')}</p>
        </div>
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPTED_EXTENSIONS.join(',')}
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) handleFile(file);
          }}
        />
      </div>
      {error && <p className="mt-2 text-sm text-destructive">{error}</p>}
    </div>
  );
}
