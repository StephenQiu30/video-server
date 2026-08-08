import {
  cancelAnalysis as cancelAnalysisRequest,
  createAnalysis as createAnalysisRequest,
  getAnalysis as getAnalysisRequest,
} from '@/services/video/analyses';

import type { AnalysisJob, CreateAnalysisInput } from '@/types/video';

export function createAnalysis(
  downloadId: string,
  input: CreateAnalysisInput,
  idempotencyKey: string,
): Promise<AnalysisJob> {
  return createAnalysisRequest(
    { download_id: encodeURIComponent(downloadId) },
    input,
    {
      headers: { 'Idempotency-Key': idempotencyKey },
    },
  );
}

export function getAnalysis(id: string): Promise<AnalysisJob> {
  return getAnalysisRequest({ analysis_id: encodeURIComponent(id) });
}

export function cancelAnalysis(id: string): Promise<AnalysisJob> {
  return cancelAnalysisRequest({ analysis_id: encodeURIComponent(id) });
}
