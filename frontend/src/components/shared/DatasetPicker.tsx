// frontend/src/components/shared/DatasetPicker.tsx
'use client';

import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { useDatasets } from '@/features/datasets/use-datasets';

/** Reusable "choose which dataset to work on" control for Analytics/KPIs/Decisions/Reports pages. */
export function DatasetPicker({
  value,
  onChange,
  placeholder = 'Choisir un jeu de donnees',
}: {
  value: string;
  onChange: (id: string) => void;
  placeholder?: string;
}) {
  const { data: datasets, isLoading } = useDatasets();

  return (
    <Select value={value} onValueChange={onChange} disabled={isLoading}>
      <SelectTrigger className="w-full sm:w-80">
        <SelectValue placeholder={isLoading ? 'Chargement...' : placeholder} />
      </SelectTrigger>
      <SelectContent>
        {datasets?.map((d) => (
          <SelectItem key={d.id} value={d.id}>
            {d.name} {d.row_count ? `(${d.row_count} lignes)` : ''}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
