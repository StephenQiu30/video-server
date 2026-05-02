declare namespace API {
  type User = {
    id: number;
    email: string;
    display_name?: string;
    is_active: boolean;
    created_at: string;
  };

  type AuthPayload = {
    email: string;
    password: string;
    display_name?: string;
  };

  type AuthResponse = {
    access_token: string;
    token_type: string;
    user: User;
  };

  type VideoFormat = {
    format_id: string;
    label: string;
    ext?: string;
    resolution?: string;
    filesize?: number;
  };

  type ParseResponse = {
    url: string;
    title?: string;
    cover_url?: string;
    duration_seconds?: number;
    formats: VideoFormat[];
  };

  type CreateTaskPayload = {
    url: string;
    format_id?: string;
    title?: string;
    cover_url?: string;
    duration_seconds?: number;
    format_label?: string;
  };

  type Task = {
    id: string;
    source_url: string;
    title?: string;
    cover_url?: string;
    duration_seconds?: number;
    format_id?: string;
    format_label?: string;
    state: 'queued' | 'running' | 'succeeded' | 'failed' | 'canceled';
    progress: number;
    failure_code?: string;
    failure_reason?: string;
    output_filename?: string;
    object_size?: number;
    expires_at?: string;
    created_at: string;
    updated_at: string;
  };

  type DownloadLink = {
    url: string;
    expires_in_seconds: number;
  };
}
