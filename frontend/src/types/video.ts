export type OutputLanguage = 'zh-CN' | 'en-US';
export type AnalysisSkill = API.AnalysisSkillResponse;
export type AnalysisStatus = API.AnalysisStatus;
export type AnalysisStage = API.AnalysisStage;
export type AnalysisShot = API.ShotResponse;
export type AnalysisHighlight = API.HighlightResponse;
export type VisualAsset = API.VisualAssetResponse;
export type AnalysisResult = NonNullable<API.AnalysisResponse['result']>;
export type VideoAnalysisResult = API.VideoAnalysisResultResponse;
export type VideoArticleResult = API.VideoArticleResultResponse;
export type ScreenplayAnalysisResult = API.ScreenplayAnalysisResultResponse;
export type ScreenplayRewriteResult = API.ScreenplayRewriteResultResponse;
export type AnalysisJob = API.AnalysisResponse;

export type CreateAnalysisInput = API.AnalysisRequest & {
  skill_id: string;
  output_language: OutputLanguage;
  custom_prompt?: string | null;
};

export type FpsBucket = API.FpsBucket;
export type DynamicRange = API.DynamicRange;
export type VideoCodec = API.VideoCodecFamily;
export type AudioCodec = API.AudioCodecFamily;
export type ContainerPreference = API.ContainerPreference;
export type CompatibilityProfile = API.CompatibilityProfile;
export type MediaKind = API.MediaKind;
export type SemanticPlan = API.SemanticPlanResponse;
export type MediaFormat = API.FormatResponse;
export type Inspection = API.InspectionResponse;
export type SourceDiscovery = API.SourceDiscoveryResponse;
export type SourceDiscoveryItem = API.SourceDiscoveryItemResponse;
export type DownloadStatus = API.DownloadStatus;
export type DownloadStage = API.DownloadStage;
export type DownloadJob = API.DownloadResponse;
export type DownloadUrl = API.DownloadUrlResponse;
export type DownloadHistoryItem = API.DownloadHistoryItemResponse;
export type DownloadHistory = API.DownloadHistoryResponse;
export type DownloadHistoryQuery = API.getDownloadHistoryParams;
export type ScreenplayDocumentStatus = API.ImportStatus;
export type ScreenplayDocumentFormat = API.DocumentSourceFormat;
export type ScreenplayDocumentSummary = API.DocumentResponse;
export type ScreenplayDocument = API.DocumentDetailResponse;
export type ScreenplayDocumentPage = API.DocumentPageResponse;
export type ScreenplayDocumentQuery = API.listDocumentsParams;

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
