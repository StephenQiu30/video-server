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

export const terminalStatuses = new Set<DownloadStatus>([
  'succeeded',
  'failed',
  'cancelled',
]);
