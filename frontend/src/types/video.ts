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

export type FpsBucket = API.FpsBucket;
export type DynamicRange = API.DynamicRange;
export type VideoCodec = API.VideoCodecFamily;
export type AudioCodec = API.AudioCodecFamily;
export type ContainerPreference = API.ContainerPreference;
export type CompatibilityProfile = API.CompatibilityProfile;
export type SemanticPlan = API.SemanticPlanResponse;
export type MediaFormat = API.FormatResponse;
export type Inspection = API.InspectionResponse;
export type DownloadStatus = API.DownloadStatus;
export type DownloadStage = API.DownloadStage;
export type DownloadJob = API.DownloadResponse;
export type DownloadUrl = API.DownloadUrlResponse;

export const terminalAnalysisStatuses = new Set<AnalysisStatus>([
  'succeeded',
  'failed',
  'cancelled',
]);

export const terminalDownloadStatuses = new Set<DownloadStatus>([
  'succeeded',
  'failed',
  'cancelled',
]);
