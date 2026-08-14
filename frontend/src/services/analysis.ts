import {
  cancelAnalysis as cancelAnalysisRequest,
  createAnalysis as createAnalysisRequest,
  createDocumentAnalysis as createDocumentAnalysisRequest,
  deleteAnalysis as deleteAnalysisRequest,
  getAnalysis as getAnalysisRequest,
  getLatestDocumentAnalysis as getLatestDocumentAnalysisRequest,
  getLatestDownloadAnalysis as getLatestDownloadAnalysisRequest,
  listAnalysisSkills as listAnalysisSkillsRequest,
  retryAnalysis as retryAnalysisRequest,
} from '@/services/video/analyses';

import type {
  AnalysisJob,
  AnalysisSkill,
  CreateAnalysisInput,
} from '@/types/video';

export function listAnalysisSkills(
  inputKind: API.AnalysisInputKind = 'video',
): Promise<AnalysisSkill[]> {
  return listAnalysisSkillsRequest({ input_kind: inputKind });
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

export function createDocumentAnalysis(
  documentId: string,
  input: CreateAnalysisInput,
  idempotencyKey: string,
): Promise<AnalysisJob> {
  return createDocumentAnalysisRequest(
    { document_id: encodeURIComponent(documentId) },
    input,
    { headers: { 'Idempotency-Key': idempotencyKey } },
  );
}

export function getAnalysis(id: string): Promise<AnalysisJob> {
  return getAnalysisRequest({ analysis_id: encodeURIComponent(id) });
}

export function getLatestDownloadAnalysis(
  downloadId: string,
): Promise<AnalysisJob | null> {
  return getLatestDownloadAnalysisRequest({
    download_id: encodeURIComponent(downloadId),
  });
}

export function getLatestDocumentAnalysis(
  documentId: string,
): Promise<AnalysisJob | null> {
  return getLatestDocumentAnalysisRequest({
    document_id: encodeURIComponent(documentId),
  });
}

export function cancelAnalysis(id: string): Promise<AnalysisJob> {
  return cancelAnalysisRequest({ analysis_id: encodeURIComponent(id) });
}

export function deleteAnalysis(id: string): Promise<void> {
  return deleteAnalysisRequest({ analysis_id: encodeURIComponent(id) });
}

export function retryAnalysis(
  id: string,
  idempotencyKey: string,
): Promise<AnalysisJob> {
  return retryAnalysisRequest(
    { analysis_id: encodeURIComponent(id) },
    { headers: { 'Idempotency-Key': idempotencyKey } },
  );
}

export function analysisReportUrl(id: string): string {
  return `/api/analyses/${encodeURIComponent(id)}/report.docx`;
}

export function analysisMarkdownUrl(id: string): string {
  return `/api/analyses/${encodeURIComponent(id)}/report.md`;
}
