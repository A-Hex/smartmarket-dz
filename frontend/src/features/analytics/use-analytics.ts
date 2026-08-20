// frontend/src/features/analytics/use-analytics.ts
'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { apiClient } from '@/lib/api-client';
import type {
  ANOVAResult,
  AnalysisJob,
  Decision,
  DescriptiveResult,
  ForecastResult,
  KPISuiteResult,
  RegressionResult,
  SegmentationResult,
  ValidationResult,
} from '@/types/api';

export function useRunDescriptive() {
  return useMutation({
    mutationFn: (dataset_id: string) =>
      apiClient.post<DescriptiveResult>('/analytics/descriptive', { dataset_id }),
  });
}

export function useRunRegression() {
  return useMutation({
    mutationFn: (payload: {
      dataset_id: string;
      target: string;
      features: string[];
      log_target?: boolean;
      interactions?: string[][];
    }) => apiClient.post<RegressionResult>('/analytics/regression', payload),
  });
}

export function useRunAnova() {
  return useMutation({
    mutationFn: (payload: { dataset_id: string; factor: string; response: string; post_hoc?: boolean }) =>
      apiClient.post<ANOVAResult>('/analytics/anova', payload),
  });
}

export function useRunValidation() {
  return useMutation({
    mutationFn: (model_id: string) => apiClient.post<ValidationResult>('/analytics/validation', { model_id }),
  });
}

export function useRunForecast() {
  return useMutation({
    mutationFn: (payload: { dataset_id: string; time_column: string; target: string; horizon?: number; train_split?: number }) =>
      apiClient.post<ForecastResult>('/analytics/forecast', payload),
  });
}

export function useRunSegmentation() {
  return useMutation({
    mutationFn: (payload: { dataset_id: string; features: string[]; algorithm?: string; k_min?: number; k_max?: number }) =>
      apiClient.post<SegmentationResult>('/analytics/segmentation', payload),
  });
}

export function useRunKpis() {
  return useMutation({
    mutationFn: (payload: {
      dataset_id: string;
      date_column?: string;
      customer_id_column?: string;
      revenue_column?: string;
      quantity_column?: string;
      price_column?: string;
      cost_column?: string;
      marketing_spend_column?: string;
      fee_column?: string;
      commission_rate?: number;
      nps_column?: string;
    }) => apiClient.post<KPISuiteResult>('/analytics/kpis', payload),
  });
}

export function useGenerateDecisions() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (dataset_id: string) =>
      apiClient.post<{ dataset_id: string; decisions: Decision[] }>('/analytics/decision', { dataset_id }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['decisions'] });
    },
  });
}

export function useJobs(type?: string) {
  return useQuery({
    queryKey: ['jobs', type],
    queryFn: () => apiClient.get<AnalysisJob[]>(`/jobs${type ? `?type=${type}` : ''}`),
  });
}
