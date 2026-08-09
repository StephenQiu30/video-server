declare namespace API {
  type AnalysisErrorCode =
    | "cancelled"
    | "analysis_cli_unavailable"
    | "analysis_cli_unsupported"
    | "analysis_cli_not_authenticated"
    | "analysis_sandbox_unavailable"
    | "analysis_media_invalid"
    | "analysis_provider_rate_limited"
    | "analysis_provider_usage_limited"
    | "analysis_cli_timeout"
    | "analysis_cli_failed"
    | "invalid_model_output"
    | "analysis_resource_limit"
    | "input_artifact_unavailable"
    | "internal_error"
    | "worker_lost";

  type AnalysisMediaResponse = {
    /** Duration Ms */
    duration_ms: number;
    /** Container */
    container: string;
    /** Size Bytes */
    size_bytes: number;
  };

  type AnalysisRequest = {
    /** Profile 视觉分镜、高光与资产分析配置。 */
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
    summary: EvidenceSummaryResponse;
    media: AnalysisMediaResponse;
    /** Shot Count */
    shot_count: number;
    /** Shots */
    shots: ShotResponse[];
    /** Highlights */
    highlights: HighlightResponse[];
    /** Assets */
    assets: VisualAssetResponse[];
  };

  type AnalysisStage = "preparing" | "analyzing" | "validating";

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

  type DownloadAnalyticsDailyResponse = {
    /** Date */
    date: string;
    /** Total */
    total: number;
    /** Succeeded */
    succeeded: number;
    /** Failed */
    failed: number;
    /** Cancelled */
    cancelled: number;
  };

  type DownloadAnalyticsResponse = {
    /** Period Days */
    period_days: number;
    /** Start */
    start: string;
    /** End */
    end: string;
    summary: DownloadAnalyticsSummaryResponse;
    /** Daily */
    daily: DownloadAnalyticsDailyResponse[];
    /** Sources */
    sources: DownloadAnalyticsSourceResponse[];
  };

  type DownloadAnalyticsSourceResponse = {
    /** Source Key */
    source_key: string;
    /** Source Name */
    source_name: string;
    /** Total */
    total: number;
    /** Succeeded */
    succeeded: number;
    /** Failed */
    failed: number;
    /** Cancelled */
    cancelled: number;
    /** Active */
    active: number;
    /** Unique Users */
    unique_users: number;
    /** Downloaded Bytes */
    downloaded_bytes: number;
    /** Success Rate */
    success_rate: number;
  };

  type DownloadAnalyticsSummaryResponse = {
    /** Total */
    total: number;
    /** Succeeded */
    succeeded: number;
    /** Failed */
    failed: number;
    /** Cancelled */
    cancelled: number;
    /** Active */
    active: number;
    /** Unique Users */
    unique_users: number;
    /** Downloaded Bytes */
    downloaded_bytes: number;
    /** Average Duration Seconds */
    average_duration_seconds: number;
    /** Success Rate */
    success_rate: number;
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

  type EvidenceSummaryResponse = {
    /** Text */
    text: string;
    /** Evidence Shot Ids */
    evidence_shot_ids: string[];
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

  type getDownloadAnalyticsParams = {
    days?: number;
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

  type HighlightResponse = {
    /** Id */
    id: string;
    /** Title */
    title: string;
    /** Description */
    description: string;
    /** Score */
    score: number;
    /** Reason */
    reason: string;
    /** Start Ms */
    start_ms: number;
    /** End Ms */
    end_ms: number;
    /** Evidence Shot Ids */
    evidence_shot_ids: string[];
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

  type listUsersParams = {
    page?: number;
    page_size?: number;
    search?: string | null;
    role?: UserRole | null;
    is_active?: boolean | null;
  };

  type LivenessResponse = {
    /** Status */
    status: string;
  };

  type ManagedUserListResponse = {
    /** Items */
    items: ManagedUserResponse[];
    /** Page */
    page: number;
    /** Page Size */
    page_size: number;
    /** Total */
    total: number;
  };

  type ManagedUserResponse = {
    /** Id */
    id: string;
    /** Username */
    username: string;
    /** Email */
    email: string;
    role: UserRole;
    /** Is Active */
    is_active: boolean;
    /** Created At */
    created_at: string;
    /** Updated At */
    updated_at: string;
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

  type RegisterRequest = {
    /** Email */
    email: string;
    /** Password */
    password: string;
    /** Username 唯一用户名，支持字母、数字、中文以及 _-. 字符。 */
    username: string;
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

  type ShotResponse = {
    /** Id */
    id: string;
    /** Index */
    index: number;
    /** Start Ms */
    start_ms: number;
    /** End Ms */
    end_ms: number;
    /** Representative Frame Ms */
    representative_frame_ms: number;
    /** Description */
    description: string;
    /** Transition In */
    transition_in: string;
    /** Shot Size */
    shot_size: string;
    /** Camera Motion */
    camera_motion: string;
    /** Visual Tags */
    visual_tags: string[];
    /** Asset Ids */
    asset_ids: string[];
  };

  type UpdateProfileRequest = {
    /** Username */
    username: string;
  };

  type updateUserAccessParams = {
    user_id: string;
  };

  type UpdateUserAccessRequest = {
    role?: UserRole | null;
    /** Is Active */
    is_active?: boolean | null;
  };

  type UserResponse = {
    /** Id */
    id: string;
    /** Username */
    username: string;
    /** Email */
    email: string;
    role: UserRole;
    /** Created At */
    created_at: string;
    /** Updated At */
    updated_at: string;
  };

  type UserRole = "admin" | "user";

  type VideoCodecFamily = "h264" | "hevc" | "vp9" | "av1" | "other";

  type VisualAssetResponse = {
    /** Id */
    id: string;
    /** Type */
    type: string;
    /** Label */
    label: string;
    /** Description */
    description: string;
    /** First Seen Ms */
    first_seen_ms: number;
    /** Evidence Shot Ids */
    evidence_shot_ids: string[];
  };
}
