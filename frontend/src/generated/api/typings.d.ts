declare namespace API {
  type AnalysisChapterResponse = {
    /** Title */
    title: string;
    /** Start Ms */
    start_ms: number;
    /** End Ms */
    end_ms: number;
    /** Summary */
    summary: string;
    /** Evidence Segment Ids */
    evidence_segment_ids: string[];
  };

  type AnalysisErrorCode =
    | "cancelled"
    | "asr_timeout"
    | "provider_rate_limited"
    | "provider_unavailable"
    | "invalid_model_output"
    | "invalid_transcript"
    | "input_artifact_unavailable"
    | "internal_error"
    | "worker_lost";

  type AnalysisRequest = {
    /** Profile */
    profile: string;
    /** Output Language */
    output_language: string;
  };

  type AnalysisResponse = {
    /** Id */
    id: string;
    /** Profile */
    profile: string;
    /** Output Language */
    output_language: string;
    status: AnalysisStatus;
    stage: AnalysisStage | null;
    /** Progress */
    progress: number;
    /** Attempt */
    attempt: number;
    error_code: AnalysisErrorCode | null;
    /** Created At */
    created_at: string;
    /** Updated At */
    updated_at: string;
    /** Finished At */
    finished_at: string | null;
    result: AnalysisResultResponse | null;
  };

  type AnalysisResultResponse = {
    /** Language */
    language: string;
    /** Title */
    title: string;
    summary: EvidenceStatementResponse;
    /** Key Points */
    key_points: EvidenceStatementResponse[];
    /** Action Items */
    action_items: EvidenceStatementResponse[];
    /** Chapters */
    chapters: AnalysisChapterResponse[];
    mind_map: MindMapNodeResponse;
  };

  type AnalysisStage =
    | "preparing"
    | "transcribing"
    | "analyzing"
    | "validating";

  type AnalysisStatus =
    | "queued"
    | "running"
    | "retry_wait"
    | "succeeded"
    | "failed"
    | "cancelled";

  type AudioCodecFamily = "aac" | "opus" | "vorbis" | "other";

  type cancelAnalysisParams = {
    analysis_id: string;
  };

  type cancelDownloadParams = {
    job_id: string;
  };

  type CompatibilityProfile = "balanced" | "quality" | "smallest";

  type ContainerPreference = "mp4" | "webm" | "source";

  type createAnalysisParams = {
    download_id: string;
  };

  type DownloadErrorCode =
    | "cancelled"
    | "download_timeout"
    | "format_unavailable"
    | "inspection_timeout"
    | "internal_error"
    | "media_validation_failed"
    | "output_limit_exceeded"
    | "storage_unavailable"
    | "temp_space_exhausted"
    | "transcode_required"
    | "unsupported_source"
    | "worker_lost";

  type DownloadRequest = {
    /** Inspection Id */
    inspection_id: string;
    /** Format Id */
    format_id: string;
  };

  type DownloadResponse = {
    /** Id */
    id: string;
    /** Inspection Id */
    inspection_id: string;
    /** Format Id */
    format_id: string;
    status: DownloadStatus;
    stage: DownloadStage | null;
    /** Progress */
    progress: number;
    /** Attempt */
    attempt: number;
    error_code: DownloadErrorCode | null;
    /** Created At */
    created_at: string;
    /** Updated At */
    updated_at: string;
    /** Finished At */
    finished_at: string | null;
  };

  type DownloadStage =
    | "revalidating"
    | "downloading"
    | "remuxing"
    | "verifying"
    | "uploading";

  type DownloadStatus =
    | "queued"
    | "running"
    | "retry_wait"
    | "succeeded"
    | "failed"
    | "cancelled";

  type DownloadUrlResponse = {
    /** Url */
    url: string;
    /** Expires At */
    expires_at: string;
  };

  type DynamicRange = "sdr" | "hdr";

  type EvidenceStatementResponse = {
    /** Text */
    text: string;
    /** Evidence Segment Ids */
    evidence_segment_ids: string[];
  };

  type FormatResponse = {
    /** Id */
    id: string;
    /** Display Name */
    display_name: string;
    plan: SemanticPlanResponse;
  };

  type FpsBucket = "fps_30" | "fps_60" | "above_60";

  type getAnalysisParams = {
    analysis_id: string;
  };

  type getDownloadParams = {
    job_id: string;
  };

  type getInspectionParams = {
    inspection_id: string;
  };

  type HTTPValidationError = {
    /** Detail */
    detail: ValidationError[] | null;
  };

  type InspectionRequest = {
    /** Url */
    url: string;
  };

  type InspectionResponse = {
    /** Id */
    id: string;
    /** Extractor Key */
    extractor_key: string;
    /** Provider Media Id */
    provider_media_id: string;
    /** Title */
    title: string;
    /** Duration Seconds */
    duration_seconds: number;
    /** Expires At */
    expires_at: string;
    /** Formats */
    formats: FormatResponse[];
  };

  type issueDownloadUrlParams = {
    job_id: string;
  };

  type MindMapNodeResponse = {
    /** Id */
    id: string;
    /** Title */
    title: string;
    /** Summary */
    summary: string | null;
    /** Start Ms */
    start_ms: number | null;
    /** Evidence Segment Ids */
    evidence_segment_ids: string[];
    /** Children */
    children: MindMapNodeResponse[];
  };

  type SemanticPlanResponse = {
    /** Height */
    height: number;
    /** Width */
    width: number;
    fps_bucket: FpsBucket;
    dynamic_range: DynamicRange;
    video_codec_family: VideoCodecFamily;
    audio_codec_family: AudioCodecFamily;
    /** Audio Language */
    audio_language: string | null;
    container_preference: ContainerPreference;
    compatibility_profile: CompatibilityProfile;
  };

  type ValidationError = {
    /** Location */
    loc: (string | number)[];
    /** Message */
    msg: string;
    /** Error Type */
    type: string;
    /** Input */
    input: any | null;
    /** Context */
    ctx: Record<string, any> | null;
  };

  type VideoCodecFamily = "h264" | "hevc" | "vp9" | "av1" | "other";
}
