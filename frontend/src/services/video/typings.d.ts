declare namespace API {
  type activateAiProviderProfileParams = {
    provider_key: string;
  };

  type AiProviderAuthMode = "host_login" | "api_key";

  type AiProviderEngine = "codex" | "claude";

  type AiProviderProfileListResponse = {
    /** Items */
    items: AiProviderProfileResponse[];
    /** Agent Available */
    agent_available: boolean;
  };

  type AiProviderProfileResponse = {
    /** Key */
    key: string;
    /** Display Name */
    display_name: string;
    engine: AiProviderEngine;
    auth_mode: AiProviderAuthMode;
    /** Base Url */
    base_url: string | null;
    /** Model */
    model: string;
    /** Credential Configured */
    credential_configured: boolean;
    /** Is Active */
    is_active: boolean;
    /** Created At */
    created_at: string;
    /** Updated At */
    updated_at: string;
  };

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
    | "analysis_input_expired"
    | "screenplay_output_incomplete"
    | "analysis_report_unavailable"
    | "internal_error"
    | "worker_lost";

  type AnalysisInputKind = "video" | "screenplay";

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
    input_kind: AnalysisInputKind;
    result_contract: AnalysisResultContract;
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
    /** Result */
    result:
      | VideoAnalysisResultResponse
      | ScreenplayAnalysisResultResponse
      | ScreenplayRewriteResultResponse
      | null;
    /** Report Markdown */
    report_markdown: string | null;
    /** Current Report Id */
    current_report_id: string | null;
    report: AnalysisReportResponse | null;
  };

  type AnalysisResultContract =
    | "video-visual-analysis"
    | "screenplay-analysis"
    | "screenplay-rewrite";

  type AnalysisSkillResponse = {
    /** Id */
    id: string;
    /** Display Name */
    display_name: string;
    /** Description */
    description: string;
    /** Default Prompt */
    default_prompt: string;
    /** Input Kinds */
    input_kinds: AnalysisInputKind[];
    result_contract: AnalysisResultContract;
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

  type cancelDocumentImportParams = {
    document_id: string;
  };

  type cancelDownloadParams = {
    job_id: string;
  };

  type CompatibilityProfile = "balanced" | "quality" | "smallest";

  type completeDocumentImportParams = {
    document_id: string;
  };

  type CompleteDocumentImportRequest = {
    /** Parts */
    parts: CompletedPartRequest[];
  };

  type CompletedPartRequest = {
    /** Part Number */
    part_number: number;
    /** Etag */
    etag: string;
  };

  type completeMediaImportParams = {
    resource_id: string;
  };

  type CompleteMediaImportRequest = {
    /** Parts */
    parts: CompletedPartRequest[];
  };

  type ContainerPreference = "mp4" | "webm" | "source";

  type CreateAiProviderProfileRequest = {
    /** Key */
    key: string;
    /** Display Name */
    display_name: string;
    engine: AiProviderEngine;
    auth_mode: AiProviderAuthMode;
    /** Base Url */
    base_url?: string | null;
    /** Model */
    model: string;
    /** Api Key */
    api_key?: string | null;
  };

  type createAnalysisParams = {
    download_id: string;
  };

  type createDocumentAnalysisParams = {
    document_id: string;
  };

  type createDocumentUploadSessionParams = {
    document_id: string;
  };

  type createMediaUploadSessionParams = {
    resource_id: string;
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

  type deleteAiProviderProfileParams = {
    provider_key: string;
  };

  type deleteAnalysisParams = {
    analysis_id: string;
  };

  type deleteDocumentParams = {
    document_id: string;
  };

  type deleteProviderCatalogEntryParams = {
    provider_key: string;
  };

  type DocumentDetailResponse = {
    /** Id */
    id: string;
    /** Title */
    title: string;
    /** Original Filename */
    original_filename: string;
    source_format: DocumentSourceFormat;
    /** Declared Size Bytes */
    declared_size_bytes: number;
    status: ImportStatus;
    /** Attempt */
    attempt: number;
    error_code: ImportErrorCode | null;
    /** Version */
    version: number;
    /** Detected Language */
    detected_language: string | null;
    /** Scene Count */
    scene_count: number | null;
    /** Character Count */
    character_count: number | null;
    /** Quality Warnings */
    quality_warnings: string[];
    /** Created At */
    created_at: string;
    /** Updated At */
    updated_at: string;
    /** Finished At */
    finished_at: string | null;
    /** Preview */
    preview: string | null;
    /** Preview Truncated */
    preview_truncated: boolean;
  };

  type DocumentImportRequest = {
    /** File Name */
    file_name: string;
    source_format: DocumentSourceFormat;
    /** Declared Size Bytes */
    declared_size_bytes: number;
    /** Declared Sha256 */
    declared_sha256: string;
    /** Rights Accepted */
    rights_accepted: boolean;
  };

  type DocumentImportResponse = {
    /** Id */
    id: string;
    source_format: DocumentSourceFormat;
    /** Original Filename */
    original_filename: string;
    /** Declared Size Bytes */
    declared_size_bytes: number;
    status: ImportStatus;
    /** Attempt */
    attempt: number;
    error_code: ImportErrorCode | null;
    /** Version */
    version: number;
    /** Created At */
    created_at: string;
    /** Updated At */
    updated_at: string;
    /** Finished At */
    finished_at: string | null;
  };

  type DocumentPageResponse = {
    /** Items */
    items: DocumentResponse[];
    /** Page */
    page: number;
    /** Page Size */
    page_size: number;
    /** Total */
    total: number;
  };

  type DocumentResponse = {
    /** Id */
    id: string;
    /** Title */
    title: string;
    /** Original Filename */
    original_filename: string;
    source_format: DocumentSourceFormat;
    /** Declared Size Bytes */
    declared_size_bytes: number;
    status: ImportStatus;
    /** Attempt */
    attempt: number;
    error_code: ImportErrorCode | null;
    /** Version */
    version: number;
    /** Detected Language */
    detected_language: string | null;
    /** Scene Count */
    scene_count: number | null;
    /** Character Count */
    character_count: number | null;
    /** Quality Warnings */
    quality_warnings: string[];
    /** Created At */
    created_at: string;
    /** Updated At */
    updated_at: string;
    /** Finished At */
    finished_at: string | null;
  };

  type DocumentSourceFormat = "docx" | "pdf" | "txt" | "markdown" | "fountain";

  type DocumentUploadSessionResponse = {
    /** Resource Id */
    resource_id: string;
    /** Attempt */
    attempt: number;
    /** Part Size Bytes */
    part_size_bytes: number;
    /** Part Count */
    part_count: number;
    /** Max Concurrency */
    max_concurrency: number;
    /** Expires At */
    expires_at: string;
    /** Parts */
    parts: UploadPartResponse[];
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
    | "provider_media_unsupported"
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
    source_kind: DownloadSourceKind;
    /** Source Label */
    source_label: string;
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
    inspection_id: string | null;
    /** Format Id */
    format_id: string | null;
    source_kind: DownloadSourceKind;
    /** Source Label */
    source_label: string;
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
    /** Title */
    title: string | null;
    /** Extractor Key */
    extractor_key: string | null;
    /** Duration Seconds */
    duration_seconds: number | null;
    /** Thumbnail Url */
    thumbnail_url: string | null;
    format: SemanticPlanResponse | null;
  };

  type DownloadSourceKind = "remote_provider" | "browser_import";

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

  type getDocumentImportParams = {
    document_id: string;
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

  type getInspectionThumbnailParams = {
    inspection_id: string;
  };

  type getLatestDocumentAnalysisParams = {
    document_id: string;
  };

  type getLatestDownloadAnalysisParams = {
    download_id: string;
  };

  type getMediaImportParams = {
    resource_id: string;
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

  type ImportErrorCode =
    | "import_storage_unavailable"
    | "upload_session_expired"
    | "upload_incomplete"
    | "import_size_mismatch"
    | "import_sha256_mismatch"
    | "video_import_invalid"
    | "document_format_unsupported"
    | "document_encrypted"
    | "document_archive_unsafe"
    | "document_text_unavailable"
    | "document_structure_invalid";

  type ImportSourceFormat =
    | "mp4"
    | "docx"
    | "pdf"
    | "txt"
    | "markdown"
    | "fountain";

  type ImportStatus =
    | "uploading"
    | "verifying"
    | "ready"
    | "failed"
    | "cancelled"
    | "expired";

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

  type listAnalysisSkillsParams = {
    input_kind: AnalysisInputKind;
  };

  type listDocumentsParams = {
    page?: number;
    page_size?: number;
  };

  type listStoredFilesParams = {
    page?: number;
    page_size?: number;
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

  type MediaImportRequest = {
    /** File Name */
    file_name: string;
    /** Declared Size Bytes */
    declared_size_bytes: number;
    /** Declared Sha256 */
    declared_sha256: string;
    /** Rights Accepted */
    rights_accepted: boolean;
  };

  type MediaImportResponse = {
    /** Id */
    id: string;
    /** Download Id */
    download_id: string;
    source_format: ImportSourceFormat;
    /** Display Name */
    display_name: string;
    /** Declared Size Bytes */
    declared_size_bytes: number;
    status: ImportStatus;
    /** Attempt */
    attempt: number;
    error_code: ImportErrorCode | null;
    /** Version */
    version: number;
    /** Created At */
    created_at: string;
    /** Updated At */
    updated_at: string;
    /** Finished At */
    finished_at: string | null;
  };

  type MediaUploadSessionResponse = {
    /** Resource Id */
    resource_id: string;
    /** Attempt */
    attempt: number;
    /** Part Size Bytes */
    part_size_bytes: number;
    /** Part Count */
    part_count: number;
    /** Max Concurrency */
    max_concurrency: number;
    /** Expires At */
    expires_at: string;
    /** Parts */
    parts: UploadPartResponse[];
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
    /** Last Media Verified At */
    last_media_verified_at: string | null;
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

  type ScreenplayAnalysisResultResponse = {
    /** Kind */
    kind: "screenplay_analysis";
    /** Language */
    language: string;
    /** Title */
    title: string;
    /** Logline */
    logline: string;
    /** Synopsis */
    synopsis: string;
    structure: ScreenplayStructureResponse;
    /** Characters */
    characters: ScreenplayCharacterResponse[];
    /** Scenes */
    scenes: ScreenplaySceneResponse[];
    /** Dialogue Findings */
    dialogue_findings: ScreenplayEvidenceItemResponse[];
    /** Strengths */
    strengths: ScreenplayEvidenceItemResponse[];
    /** Priority Revisions */
    priority_revisions: ScreenplayEvidenceItemResponse[];
  };

  type ScreenplayCharacterResponse = {
    /** Id */
    id: string;
    /** Name */
    name: string;
    /** Goal */
    goal: string;
    /** Conflict */
    conflict: string;
    /** Arc */
    arc: string;
    /** Evidence Scene Ids */
    evidence_scene_ids: string[];
  };

  type ScreenplayEvidenceItemResponse = {
    /** Id */
    id: string;
    /** Title */
    title: string;
    /** Description */
    description: string;
    /** Evidence Scene Ids */
    evidence_scene_ids: string[];
  };

  type ScreenplayGlossaryTermResponse = {
    /** Source */
    source: string;
    /** Target */
    target: string;
    /** Category */
    category: string;
  };

  type ScreenplayRewriteResultResponse = {
    /** Kind */
    kind: "screenplay_rewrite";
    /** Source Language */
    source_language: string;
    /** Target Language */
    target_language: string;
    /** Source Scene Count */
    source_scene_count: number;
    /** Output Scene Count */
    output_scene_count: number;
    /** Glossary */
    glossary: ScreenplayGlossaryTermResponse[];
    /** Change Summary */
    change_summary: string[];
  };

  type ScreenplaySceneResponse = {
    /** Id */
    id: string;
    /** Source Scene Id */
    source_scene_id: string;
    /** Purpose */
    purpose: string;
    /** Conflict */
    conflict: string;
    /** Turn */
    turn: string;
    /** Pacing */
    pacing: string;
    /** Findings */
    findings: string[];
  };

  type ScreenplayStructureResponse = {
    /** Acts */
    acts: ScreenplayEvidenceItemResponse[];
    /** Turning Points */
    turning_points: ScreenplayEvidenceItemResponse[];
    /** Pacing Summary */
    pacing_summary: string;
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

  type StorageCleanupRequest = {
    /** Older Than Days */
    older_than_days?: number;
  };

  type StorageCleanupResponse = {
    /** Older Than Days */
    older_than_days: number;
    /** Removed Resources */
    removed_resources: number;
    /** Removed Objects */
    removed_objects: number;
    /** Freed Bytes */
    freed_bytes: number;
    /** Failed Resources */
    failed_resources: number;
  };

  type StoredFileCategory = "video" | "screenplay" | "analysis_report";

  type StoredFileListResponse = {
    /** Items */
    items: StoredFileResponse[];
    /** Page */
    page: number;
    /** Page Size */
    page_size: number;
    /** Total */
    total: number;
  };

  type StoredFileResponse = {
    /** Id */
    id: string;
    category: StoredFileCategory;
    /** Name */
    name: string;
    /** Object Count */
    object_count: number;
    /** Size Bytes */
    size_bytes: number;
    /** Created At */
    created_at: string;
  };

  type updateAiProviderProfileParams = {
    provider_key: string;
  };

  type UpdateAiProviderProfileRequest = {
    /** Display Name */
    display_name?: string | null;
    engine?: AiProviderEngine | null;
    auth_mode?: AiProviderAuthMode | null;
    /** Base Url */
    base_url?: string | null;
    /** Model */
    model?: string | null;
    /** Api Key */
    api_key?: string | null;
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

  type UploadPartResponse = {
    /** Part Number */
    part_number: number;
    /** Url */
    url: string;
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

  type VideoAnalysisResultResponse = {
    /** Kind */
    kind: "video_visual_analysis";
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
