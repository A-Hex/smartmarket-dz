// frontend/src/features/cleaning/use-cleaning.ts
'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';

import { apiClient } from '@/lib/api-client';

export type MissingStrategy = 'mean' | 'median' | 'mode' | 'constant' | 'drop_rows' | 'drop_column' | 'none';
export type OutlierMethod = 'iqr' | 'zscore' | 'none';
export type OutlierAction = 'remove' | 'cap' | 'none';

export interface ColumnCleaningConfig {
  column: string;
  missing_strategy: MissingStrategy;
  constant_value?: string | number | null;
  outlier_method: OutlierMethod;
  outlier_action: OutlierAction;
}

export interface ColumnCleaningReport {
  column: string;
  null_count_before: number;
  null_count_after: number;
  outliers_detected: number;
  outliers_handled: number;
  strategy_applied: string;
}

export interface CleaningReport {
  rows_before: number;
  rows_after: number;
  columns_before: number;
  columns_after: number;
  per_column: ColumnCleaningReport[];
  cleaned_storage_path: string;
}

export interface CleaningRunResult {
  id: string;
  dataset_id: string;
  status: string;
  report: CleaningReport | null;
}

export function useRunCleaning(datasetId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (columns: ColumnCleaningConfig[]) =>
      apiClient.post<CleaningRunResult>(`/datasets/${datasetId}/cleaning`, { columns }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['datasets', datasetId] });
    },
  });
}
