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
    | "analysis_report_unavailable"
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

  type AnalysisReportArtifactResponse = {
    /** Format */
    format: string;
    /** Media Type */
    media_type: string;
    /** Size Bytes */
    size_bytes: number;
    /** Sha256 */
    sha256: string;
  };

  type AnalysisReportResponse = {
    /** Id */
    id: string;
    /** Status */
    status: string;
    /** Renderer Version */
    renderer_version: string;
    /** Content Sha256 */
    content_sha256: string;
    /** Published At */
    published_at: string | null;
    /** Artifacts */
    artifacts: AnalysisReportArtifactResponse[];
  };

  type AnalysisRequest = {
    /** Skill Id 分析 Skill 的稳定标识，由分析 Skill 清单接口提供。 */
    skill_id: string;
    /** Output Language 分析结果使用的 BCP 47 语言标签。 */
    output_language: string;
    /** Custom Prompt 用户可编辑的分析要求，仅影响观察重点和表达，不能覆盖工具、安全边界或结果结构。 */
    custom_prompt?: string | null;
  };

  type AnalysisResponse = {
    /** Id */
    id: string;
    /** Run Id */
    run_id: string;
    /** Run No */
    run_no: number;
    /** Run Trigger */
    run_trigger: string;
    /** Version */
    version: number;
    /** Skill Id */
    skill_id: string;
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
    /** Report Markdown */
    report_markdown: string | null;
    /** Current Report Id */
    current_report_id: string | null;
    /** Retry Available Until */
    retry_available_until: string | null;
    report: AnalysisReportResponse | null;
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
    production_advice: ProductionAdviceResponse;
  };

  type AnalysisSkillResponse = {
    /** Id */
    id: string;
    /** Display Name */
    display_name: string;
    /** Description */
    description: string;
    /** Default Prompt */
    default_prompt: string;
  };

  type AnalysisStage = "preparing" | "analyzing" | "validating" | "publishing";

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

  type CreateProviderCatalogEntryRequest = {
    /** Key */
    key: string;
    /** Display Name */
    display_name: string;
    /** Sort Order */
    sort_order: number;
    /** Is Visible */
    is_visible?: boolean;
  };

  type deleteAnalysisParams = {
    analysis_id: string;
  };

  type deleteProviderCatalogEntryParams = {
    provider_key: string;
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
    | "provider_auth_required"
    | "provider_content_restricted"
    | "provider_drm_protected"
    | "provider_geo_restricted"
    | "provider_link_unavailable"
    | "provider_rate_limited"
    | "provider_session_expired"
    | "provider_temporarily_unavailable"
    | "provider_unsupported"
    | "provider_verification_failed"
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
    /** File Available */
    file_available: boolean;
    /** File Expires At */
    file_expires_at: string | null;
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
    /** Version */
    version: number;
    error_code: DownloadErrorCode | null;
    /** Created At */
    created_at: string;
    /** Updated At */
    updated_at: string;
    /** Finished At */
    finished_at: string | null;
    /** File Available */
    file_available: boolean;
    /** File Expires At */
    file_expires_at: string | null;
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

  type exportAnalysisMarkdownParams = {
    analysis_id: string;
  };

  type exportAnalysisReportParams = {
    analysis_id: string;
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

  type getLatestDownloadAnalysisParams = {
    download_id: string;
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

  type ProductionAdviceResponse = {
    /** Summary */
    summary: string;
    /** Priority Shot Ids */
    priority_shot_ids: string[];
    /** Recommended Extensions */
    recommended_extensions: string[];
  };

  type ProviderAccessMode = "anonymous" | "operator_managed";

  type ProviderCapability =
    | "single_video"
    | "short_video"
    | "clip_or_vod"
    | "audio_video_split"
    | "subtitles"
    | "image_or_carousel"
    | "live"
    | "playlist";

  type ProviderCatalogEntryResponse = {
    /** Key */
    key: string;
    /** Display Name */
    display_name: string;
    /** Sort Order */
    sort_order: number;
    /** Is Visible */
    is_visible: boolean;
    /** System Registered */
    system_registered: boolean;
    system_status: ProviderSupportStatus;
    /** Created At */
    created_at: string;
    /** Updated At */
    updated_at: string;
  };

  type ProviderCatalogListResponse = {
    /** Items */
    items: ProviderCatalogEntryResponse[];
  };

  type ProviderListResponse = {
    /** Items */
    items: ProviderStatusResponse[];
  };

  type ProviderStatusResponse = {
    /** Key */
    key: string;
    /** Display Name */
    display_name: string;
    /** Registered */
    registered: boolean;
    /** Extractor Exists */
    extractor_exists: boolean;
    /** Capabilities */
    capabilities: ProviderCapability[];
    /** Access Modes */
    access_modes: ProviderAccessMode[];
    status: ProviderSupportStatus;
    /** Last Verified At */
    last_verified_at: string | null;
    /** User Action */
    user_action: string | null;
  };

  type ProviderSupportStatus =
    | "unknown"
    | "verified"
    | "degraded"
    | "access_required"
    | "rate_limited"
    | "blocked"
    | "disabled"
    | "unsupported";

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

  type retryAnalysisParams = {
    analysis_id: string;
  };

  type retryDownloadParams = {
    job_id: string;
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
    /** Narrative Function */
    narrative_function: string;
    /** Highlight Score */
    highlight_score: number;
    /** Visual Tags */
    visual_tags: string[];
    /** Asset Ids */
    asset_ids: string[];
  };

  type UpdateProfileRequest = {
    /** Username */
    username: string;
  };

  type updateProviderCatalogEntryParams = {
    provider_key: string;
  };

  type UpdateProviderCatalogEntryRequest = {
    /** Display Name */
    display_name?: string | null;
    /** Sort Order */
    sort_order?: number | null;
    /** Is Visible */
    is_visible?: boolean | null;
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
