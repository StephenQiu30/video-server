declare namespace API {
  type VideoFormat = {
    format_id: string;
    label: string;
    ext?: string;
    resolution?: string;
    filesize?: number;
    quality_label?: string;
    height?: number;
    width?: number;
    kind?: 'recommended' | 'video' | 'raw';
    available?: boolean;
    note?: string;
  };

  type ParseResponse = {
    url: string;
    title?: string;
    cover_url?: string;
    duration_seconds?: number;
    source_site?: string;
    extractor?: string;
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

  type TaskEvent = {
    id: number;
    task_id: string;
    state: Task['state'] | string;
    message?: string;
    created_at: string;
  };

  type DownloadLink = {
    url: string;
    expires_in_seconds: number;
  };

  type ReadinessCheck = {
    ok: boolean;
    message?: string;
    [key: string]: string | number | boolean | undefined;
  };

  type Readiness = {
    status: 'ok' | 'degraded';
    checks: Record<string, ReadinessCheck>;
  };
}
