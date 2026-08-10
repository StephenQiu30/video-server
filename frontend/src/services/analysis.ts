import {
  cancelAnalysis as cancelAnalysisRequest,
  createAnalysis as createAnalysisRequest,
  getAnalysis as getAnalysisRequest,
  listAnalysisSkills as listAnalysisSkillsRequest,
} from '@/services/video/analyses';

import type {
  AnalysisJob,
  AnalysisSkill,
  CreateAnalysisInput,
} from '@/types/video';

export function listAnalysisSkills(): Promise<AnalysisSkill[]> {
  return listAnalysisSkillsRequest();
}

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

export function analysisReportUrl(id: string): string {
  return `/api/analyses/${encodeURIComponent(id)}/report.docx`;
}

export function analysisMarkdownUrl(id: string): string {
  return `/api/analyses/${encodeURIComponent(id)}/report.md`;
}
