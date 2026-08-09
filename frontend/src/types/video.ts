export type AnalysisProfile = 'visual-shot-v1';
export type OutputLanguage = 'zh-CN' | 'en-US';
export type AnalysisStatus = API.AnalysisStatus;
export type AnalysisStage = API.AnalysisStage;
export type AnalysisShot = API.ShotResponse;
export type AnalysisHighlight = API.HighlightResponse;
export type VisualAsset = API.VisualAssetResponse;
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
export type DownloadHistoryItem = API.DownloadHistoryItemResponse;
export type DownloadHistory = API.DownloadHistoryResponse;
export type DownloadHistoryQuery = API.getDownloadHistoryParams;

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
