export type AnalysisProfile = 'standard-v1';
export type OutputLanguage = 'zh-CN' | 'en-US';
export type AnalysisStatus = API.AnalysisStatus;
export type AnalysisStage = API.AnalysisStage;
export type EvidenceStatement = API.EvidenceStatementResponse;
export type AnalysisChapter = API.AnalysisChapterResponse;
export type MindMapNode = API.MindMapNodeResponse;
export type AnalysisResult = API.AnalysisResultResponse;
export type AnalysisJob = API.AnalysisResponse;

export type CreateAnalysisInput = API.AnalysisRequest & {
  profile: AnalysisProfile;
  output_language: OutputLanguage;
};

export const terminalAnalysisStatuses = new Set<AnalysisStatus>([
  'succeeded',
  'failed',
  'cancelled',
]);
