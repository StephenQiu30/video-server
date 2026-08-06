import {
  cancelAnalysisApiV1AnalysesAnalysisIdCancelPost,
  createAnalysisApiV1DownloadsDownloadIdAnalysesPost,
  getAnalysisApiV1AnalysesAnalysisIdGet,
} from '@/services/video/analyses';

import type { AnalysisJob, CreateAnalysisInput } from '@/types/video';

export function createAnalysis(
  downloadId: string,
  input: CreateAnalysisInput,
  idempotencyKey: string,
): Promise<AnalysisJob> {
  return createAnalysisApiV1DownloadsDownloadIdAnalysesPost(
    { download_id: downloadId },
    input,
    { headers: { 'Idempotency-Key': idempotencyKey } },
  );
}

export function getAnalysis(id: string): Promise<AnalysisJob> {
  return getAnalysisApiV1AnalysesAnalysisIdGet({ analysis_id: id });
}

export function cancelAnalysis(id: string): Promise<AnalysisJob> {
  return cancelAnalysisApiV1AnalysesAnalysisIdCancelPost({ analysis_id: id });
}
