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
    /** Profile 服务支持的结构化分析配置。 */
    profile: string;
    /** Output Language 分析结果使用的 BCP 47 语言标签。 */
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

  type DownloadHistoryItemResponse = {
    /** Id */
    id: string;
    /** Title */
    title: string;
    /** Thumbnail Url */
    thumbnail_url: string | null;
    /** Format Name */
    format_name: string;
    status: DownloadStatus;
    /** Progress */
    progress: number;
    error_code: DownloadErrorCode | null;
    /** Created At */
    created_at: string;
    /** Updated At */
    updated_at: string;
    /** Finished At */
    finished_at: string | null;
  };

  type DownloadHistoryResponse = {
    /** Items */
    items: DownloadHistoryItemResponse[];
    /** Page */
    page: number;
    /** Page Size */
    page_size: number;
    /** Total */
    total: number;
    summary: DownloadHistorySummaryResponse;
  };

  type DownloadHistorySummaryResponse = {
    /** Total */
    total: number;
    /** Succeeded */
    succeeded: number;
    /** Active */
    active: number;
    /** Failed */
    failed: number;
  };

  type DownloadRequest = {
    /** Inspection Id 仍在有效期内的媒体解析资源 ID。 */
    inspection_id: string;
    /** Format Id 解析结果中选择的语义下载格式 ID。 */
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

  type EmailPasswordRequest = {
    /** Email */
    email: string;
    /** Password */
    password: string;
  };

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

  type getDownloadHistoryParams = {
    page?: number;
    page_size?: number;
    status?: DownloadStatus | null;
    search?: string | null;
  };

  type getDownloadParams = {
    job_id: string;
  };

  type getInspectionParams = {
    inspection_id: string;
  };

  type InspectionRequest = {
    /** Url 用户有权处理的公开、非 DRM HTTP(S) 媒体地址。 */
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
    /** Thumbnail Url */
    thumbnail_url: string | null;
    /** Expires At */
    expires_at: string;
    /** Formats */
    formats: FormatResponse[];
  };

  type issueDownloadUrlParams = {
    job_id: string;
  };

  type LivenessResponse = {
    /** Status */
    status: string;
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

  type ProblemDetails = {
    /** Type 稳定的服务错误类型 URI。 */
    type: string;
    /** Title 面向调用方的简短错误标题。 */
    title: string;
    /** Status HTTP 状态码。 */
    status: number;
    /** Detail 不包含敏感信息的错误说明。 */
    detail: string;
    /** Code 供客户端分支处理的稳定错误码。 */
    code: string;
    /** Instance 产生错误的请求路径。 */
    instance: string;
  };

  type ReadinessResponse = {
    /** Status */
    status: "ok" | "unavailable";
    /** Service */
    service: string;
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

  type UserResponse = {
    /** Id */
    id: string;
    /** Email */
    email: string;
    /** Created At */
    created_at: string;
  };

  type VideoCodecFamily = "h264" | "hevc" | "vp9" | "av1" | "other";
}
