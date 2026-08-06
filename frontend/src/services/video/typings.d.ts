declare namespace API {
  type ArtifactSummary = {
    /** File Name */
    file_name: string;
    /** Content Type */
    content_type: string;
    /** Size Bytes */
    size_bytes: number;
    /** Sha256 */
    sha256: string;
    /** Expires At */
    expires_at: string;
  };

  type CreateDownloadRequest = {
    /** Source Id */
    source_id: string;
    /** Format Id */
    format_id: string;
    /** Client Request Id */
    client_request_id: string;
  };

  type createDownloadUrlParams = {
    job_id: string;
  };

  type DownloadJob = {
    /** Id */
    id: string;
    /** Status */
    status: "queued" | "running" | "succeeded" | "failed" | "expired";
    /** Stage */
    stage?: "downloading" | "merging" | "verifying" | "uploading" | null;
    /** Progress Percent */
    progress_percent?: number | null;
    /** Downloaded Bytes */
    downloaded_bytes?: number | null;
    /** Total Bytes */
    total_bytes?: number | null;
    error?: JobError | null;
    artifact?: ArtifactSummary | null;
    /** Created At */
    created_at: string;
    /** Updated At */
    updated_at: string;
  };

  type DownloadUrl = {
    /** Url */
    url: string;
    /** Expires At */
    expires_at: string;
    /** File Name */
    file_name: string;
  };

  type getDownloadParams = {
    job_id: string;
  };

  type InspectedMedia = {
    /** Id */
    id: string;
    /** Title */
    title: string;
    /** Platform */
    platform: string;
    /** Thumbnail Url */
    thumbnail_url?: string | null;
    /** Duration Seconds */
    duration_seconds?: number | null;
    /** Expires At */
    expires_at: string;
    /** Formats */
    formats: MediaFormat[];
  };

  type InspectMediaRequest = {
    /** Url */
    url: string;
  };

  type JobError = {
    /** Code */
    code: string;
    /** Message */
    message: string;
  };

  type MediaFormat = {
    /** Id */
    id: string;
    /** Label */
    label: string;
    /** Width */
    width?: number | null;
    /** Height */
    height?: number | null;
    /** Fps */
    fps?: number | null;
    /** Container */
    container: string;
    /** Video Codec */
    video_codec: string;
    /** Audio Codec */
    audio_codec: string;
    /** Estimated Size Bytes */
    estimated_size_bytes?: number | null;
    /** Requires Merge */
    requires_merge: boolean;
  };

  type ProblemDetails = {
    /** Type */
    type?: string;
    /** Title */
    title: string;
    /** Status */
    status: number;
    /** Detail */
    detail: string;
    /** Code */
    code: string;
    /** Details */
    details?: any | null;
  };
}
