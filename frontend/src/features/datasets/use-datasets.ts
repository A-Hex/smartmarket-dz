// frontend/src/features/datasets/use-datasets.ts
'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { apiClient } from '@/lib/api-client';
import type { Dataset, DatasetDetail, DatasetPreview } from '@/types/api';

export function useDatasets() {
  return useQuery({
    queryKey: ['datasets'],
    queryFn: () => apiClient.get<Dataset[]>('/datasets'),
  });
}

export function useDataset(id: string | undefined) {
  return useQuery({
    queryKey: ['datasets', id],
    queryFn: () => apiClient.get<DatasetDetail>(`/datasets/${id}`),
    enabled: !!id,
  });
}

export function useDatasetPreview(id: string | undefined, limit = 50) {
  return useQuery({
    queryKey: ['datasets', id, 'preview', limit],
    queryFn: () => apiClient.get<DatasetPreview>(`/datasets/${id}/preview?limit=${limit}`),
    enabled: !!id,
  });
}

export function useUploadDataset() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => {
      const formData = new FormData();
      formData.append('file', file);
      return apiClient.post<DatasetDetail>('/datasets', formData, { isFormData: true });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['datasets'] });
    },
  });
}

export function useDeleteDataset() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => apiClient.delete(`/datasets/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['datasets'] });
    },
  });
}
