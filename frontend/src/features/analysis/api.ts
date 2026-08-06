import { request } from '@/shared/api/client';

import type { AnalysisJob, CreateAnalysisInput } from './types';

export function createAnalysis(
  downloadId: string,
  input: CreateAnalysisInput,
  idempotencyKey: string,
): Promise<AnalysisJob> {
  return request(
    `/api/v1/downloads/${encodeURIComponent(downloadId)}/analyses`,
    {
      method: 'POST',
      headers: { 'Idempotency-Key': idempotencyKey },
      data: input,
    },
  );
}

export function getAnalysis(id: string): Promise<AnalysisJob> {
  return request(`/api/v1/analyses/${encodeURIComponent(id)}`);
}

export function cancelAnalysis(id: string): Promise<AnalysisJob> {
  return request(`/api/v1/analyses/${encodeURIComponent(id)}/cancel`, {
    method: 'POST',
  });
}
