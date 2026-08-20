// frontend/src/features/reports/use-reports.ts
'use client';

import { useMutation } from '@tanstack/react-query';

import { apiClient } from '@/lib/api-client';
import type { Report, ReportFormat } from '@/types/api';

export function useGenerateReport() {
  return useMutation({
    mutationFn: (payload: { dataset_id: string; format: ReportFormat }) =>
      apiClient.post<Report>('/reports/generate', payload),
  });
}

/** Downloads a report and triggers a browser save via a temporary object URL. */
export async function downloadReport(report: Report): Promise<void> {
  const blob = await apiClient.getBlob(`/reports/${report.id}/download`);
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `smartmarket-${report.type}.${report.format}`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url);
}
