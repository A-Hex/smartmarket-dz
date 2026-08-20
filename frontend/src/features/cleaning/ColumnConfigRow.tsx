// frontend/src/features/cleaning/ColumnConfigRow.tsx
'use client';

import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import type { DatasetColumn } from '@/types/api';

import type { ColumnCleaningConfig, MissingStrategy, OutlierAction, OutlierMethod } from './use-cleaning';

const MISSING_OPTIONS: { value: MissingStrategy; label: string }[] = [
  { value: 'none', label: 'Aucune action' },
  { value: 'mean', label: 'Remplacer par la moyenne' },
  { value: 'median', label: 'Remplacer par la mediane' },
  { value: 'mode', label: 'Remplacer par le mode' },
  { value: 'drop_rows', label: 'Supprimer les lignes' },
  { value: 'drop_column', label: 'Supprimer la colonne' },
];

const OUTLIER_METHOD_OPTIONS: { value: OutlierMethod; label: string }[] = [
  { value: 'none', label: 'Aucune detection' },
  { value: 'iqr', label: 'IQR (ecart interquartile)' },
  { value: 'zscore', label: 'Score-z' },
];

const OUTLIER_ACTION_OPTIONS: { value: OutlierAction; label: string }[] = [
  { value: 'none', label: 'Aucune action' },
  { value: 'cap', label: 'Plafonner (winsoriser)' },
  { value: 'remove', label: 'Supprimer les lignes' },
];

export function ColumnConfigRow({
  column, config, onChange,
}: { column: DatasetColumn; config: ColumnCleaningConfig; onChange: (next: ColumnCleaningConfig) => void }) {
  return (
    <tr className="border-t border-border">
      <td className="px-3 py-2">
        <p className="font-medium">{column.name}</p>
        <p className="text-xs text-muted-foreground">
          {column.dtype} &middot; {column.null_count} manquant(s)
        </p>
      </td>
      <td className="px-3 py-2">
        <Select
          value={config.missing_strategy}
          onValueChange={(v) => onChange({ ...config, missing_strategy: v as MissingStrategy })}
        >
          <SelectTrigger className="w-48"><SelectValue /></SelectTrigger>
          <SelectContent>
            {MISSING_OPTIONS.map((o) => <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>)}
          </SelectContent>
        </Select>
      </td>
      <td className="px-3 py-2">
        <Select
          value={config.outlier_method}
          onValueChange={(v) => onChange({ ...config, outlier_method: v as OutlierMethod })}
        >
          <SelectTrigger className="w-44"><SelectValue /></SelectTrigger>
          <SelectContent>
            {OUTLIER_METHOD_OPTIONS.map((o) => <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>)}
          </SelectContent>
        </Select>
      </td>
      <td className="px-3 py-2">
        <Select
          value={config.outlier_action}
          onValueChange={(v) => onChange({ ...config, outlier_action: v as OutlierAction })}
          disabled={config.outlier_method === 'none'}
        >
          <SelectTrigger className="w-44"><SelectValue /></SelectTrigger>
          <SelectContent>
            {OUTLIER_ACTION_OPTIONS.map((o) => <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>)}
          </SelectContent>
        </Select>
      </td>
    </tr>
  );
}
