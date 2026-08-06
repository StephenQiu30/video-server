export type FpsBucket = 'fps_30' | 'fps_60' | 'above_60';
export type DynamicRange = 'sdr' | 'hdr';
export type VideoCodec = 'h264' | 'hevc' | 'vp9' | 'av1' | 'other';
export type AudioCodec = 'aac' | 'opus' | 'vorbis' | 'other';
export type ContainerPreference = 'mp4' | 'webm' | 'source';
export type CompatibilityProfile = 'balanced' | 'quality' | 'smallest';

export type SemanticPlan = {
  height: number;
  width: number;
  fps_bucket: FpsBucket;
  dynamic_range: DynamicRange;
  video_codec_family: VideoCodec;
  audio_codec_family: AudioCodec;
  audio_language: string | null;
  container_preference: ContainerPreference;
  compatibility_profile: CompatibilityProfile;
};

export type MediaFormat = {
  id: string;
  display_name: string;
  plan: SemanticPlan;
};

export type Inspection = {
  id: string;
  extractor_key: string;
  provider_media_id: string;
  title: string;
  duration_seconds: number;
  expires_at: string;
  formats: MediaFormat[];
};

export type DownloadStatus =
  | 'queued'
  | 'running'
  | 'retry_wait'
  | 'succeeded'
  | 'failed'
  | 'cancelled';

export type DownloadStage =
  | 'revalidating'
  | 'downloading'
  | 'remuxing'
  | 'verifying'
  | 'uploading';

export type DownloadJob = {
  id: string;
  inspection_id: string;
  format_id: string;
  status: DownloadStatus;
  stage: DownloadStage | null;
  progress: number;
  attempt: number;
  error_code: string | null;
  created_at: string;
  updated_at: string;
  finished_at: string | null;
};

export type DownloadUrl = {
  url: string;
  expires_at: string;
};

export const terminalStatuses = new Set<DownloadStatus>([
  'succeeded',
  'failed',
  'cancelled',
]);
