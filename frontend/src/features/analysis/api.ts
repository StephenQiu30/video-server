import { apiRequest, jsonPost } from '@/shared/api/client';

import type { AnalysisJob, CreateAnalysisInput } from './types';

export function createAnalysis(
  downloadId: string,
  input: CreateAnalysisInput,
  idempotencyKey: string,
): Promise<AnalysisJob> {
  return apiRequest(
    `/downloads/${encodeURIComponent(downloadId)}/analyses`,
    jsonPost(input, idempotencyKey),
  );
}

export function getAnalysis(id: string): Promise<AnalysisJob> {
  return apiRequest(`/analyses/${encodeURIComponent(id)}`);
}

export function cancelAnalysis(id: string): Promise<AnalysisJob> {
  return apiRequest(`/analyses/${encodeURIComponent(id)}/cancel`, jsonPost());
}
