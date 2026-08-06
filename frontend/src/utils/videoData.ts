export type MediaFormat = {
  id: string;
  label: string;
  width: number | null;
  height: number | null;
  fps: number | null;
  container: string | null;
  videoCodec: string | null;
  audioCodec: string | null;
  estimatedSizeBytes: number | null;
  requiresMerge: boolean;
};

export type MediaSummary = {
  id: string;
  title: string;
  platform: string;
  thumbnailUrl: string | null;
  durationSeconds: number | null;
  expiresAt: string;
  formats: MediaFormat[];
};

export type DownloadJob = {
  id: string;
  status: 'queued' | 'running' | 'succeeded' | 'failed' | 'expired';
  stage: string | null;
  progressPercent: number | null;
  downloadedBytes: number | null;
  totalBytes: number | null;
  error: unknown;
  artifact: unknown;
  createdAt: string | null;
  updatedAt: string | null;
};

function record(value: unknown): Record<string, unknown> | null {
  return typeof value === 'object' && value !== null
    ? (value as Record<string, unknown>)
    : null;
}

function stringValue(value: unknown): string | null {
  return typeof value === 'string' && value.trim() ? value : null;
}

function numberValue(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

function booleanValue(value: unknown): boolean {
  return value === true;
}

export function parseMediaSummary(value: unknown): MediaSummary | null {
  const data = record(value);
  if (!data) return null;
  const id = stringValue(data.id);
  const expiresAt = stringValue(data.expires_at);
  const formats = Array.isArray(data.formats)
    ? data.formats
        .map(parseMediaFormat)
        .filter((item): item is MediaFormat => item !== null)
    : [];
  if (!id || !expiresAt || formats.length === 0) return null;
  return {
    id,
    title: stringValue(data.title) ?? '未命名视频',
    platform: stringValue(data.platform) ?? '未知平台',
    thumbnailUrl: stringValue(data.thumbnail_url),
    durationSeconds: numberValue(data.duration_seconds),
    expiresAt,
    formats,
  };
}

function parseMediaFormat(value: unknown): MediaFormat | null {
  const data = record(value);
  const id = data && stringValue(data.id);
  const label = data && stringValue(data.label);
  if (!id || !label) return null;
  return {
    id,
    label,
    width: data ? numberValue(data.width) : null,
    height: data ? numberValue(data.height) : null,
    fps: data ? numberValue(data.fps) : null,
    container: data ? stringValue(data.container) : null,
    videoCodec: data ? stringValue(data.video_codec) : null,
    audioCodec: data ? stringValue(data.audio_codec) : null,
    estimatedSizeBytes: data ? numberValue(data.estimated_size_bytes) : null,
    requiresMerge: data ? booleanValue(data.requires_merge) : false,
  };
}

export function parseDownloadJob(value: unknown): DownloadJob | null {
  const data = record(value);
  if (!data) return null;
  const id = stringValue(data.id);
  const status = stringValue(data.status);
  if (
    !id ||
    !status ||
    !['queued', 'running', 'succeeded', 'failed', 'expired'].includes(status)
  ) {
    return null;
  }
  return {
    id,
    status: status as DownloadJob['status'],
    stage: stringValue(data.stage),
    progressPercent: numberValue(data.progress_percent),
    downloadedBytes: numberValue(data.downloaded_bytes),
    totalBytes: numberValue(data.total_bytes),
    error: data.error ?? null,
    artifact: data.artifact ?? null,
    createdAt: stringValue(data.created_at),
    updatedAt: stringValue(data.updated_at),
  };
}

export function parseJobId(value: unknown): string | null {
  const data = record(value);
  return data ? stringValue(data.id) : null;
}

export function parseDownloadUrl(
  value: unknown,
): { url: string; expiresAt: string | null } | null {
  const data = record(value);
  const url = data && stringValue(data.url);
  if (!url) return null;
  try {
    const parsed = new URL(url);
    if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:')
      return null;
  } catch {
    return null;
  }
  return { url, expiresAt: data ? stringValue(data.expires_at) : null };
}

export function isExpired(expiresAt: string, now = Date.now()): boolean {
  const timestamp = Date.parse(expiresAt);
  return !Number.isFinite(timestamp) || timestamp <= now;
}

export function formatBytes(value: number | null): string {
  if (value === null || value < 0) return '大小未知';
  if (value < 1024) return `${value} B`;
  const units = ['KB', 'MB', 'GB'];
  let size = value / 1024;
  let index = 0;
  while (size >= 1024 && index < units.length - 1) {
    size /= 1024;
    index += 1;
  }
  return `${size.toFixed(size >= 10 ? 0 : 1)} ${units[index]}`;
}

export function formatDuration(value: number | null): string {
  if (value === null || value < 0) return '时长未知';
  const seconds = Math.round(value);
  const minutes = Math.floor(seconds / 60);
  return `${minutes}:${String(seconds % 60).padStart(2, '0')}`;
}
