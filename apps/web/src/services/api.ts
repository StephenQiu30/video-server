export const API_BASE_URL = process.env.UMI_APP_API_BASE_URL || 'http://127.0.0.1:8000';

export function normalizeUserUrl(value: string) {
  const url = value.trim();
  if (!url) throw new Error('请输入视频链接');
  if (/\s/.test(url)) throw new Error('请输入有效的视频链接，例如 https://example.com/video');
  const normalizedUrl = /^https?:\/\//i.test(url) ? url : `https://${url}`;
  let parsed: URL;
  try {
    parsed = new URL(normalizedUrl);
  } catch {
    throw new Error('请输入有效的视频链接，例如 https://example.com/video');
  }
  if (!['http:', 'https:'].includes(parsed.protocol) || !isValidHostname(parsed.hostname)) {
    throw new Error('请输入有效的视频链接，例如 https://example.com/video');
  }
  return normalizedUrl;
}

function isValidHostname(hostname: string) {
  if (!hostname) return false;
  if (hostname === 'localhost' || hostname.includes('.')) return true;
  return /^\d{1,3}(\.\d{1,3}){3}$/.test(hostname) || hostname.includes(':');
}

function getErrorMessage(data: any) {
  if (data?.error?.message) return data.error.message;
  if (typeof data?.message === 'string') return data.message;
  if (typeof data?.detail === 'string') return data.detail;
  if (Array.isArray(data?.detail)) {
    return data.detail
      .map((item: { msg?: string }) => item?.msg)
      .filter(Boolean)
      .join('；');
  }
  return '请求失败，请稍后重试';
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set('Content-Type', 'application/json');
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  });
  const text = await response.text();
  const data = text ? JSON.parse(text) : undefined;
  if (!response.ok) {
    throw new Error(getErrorMessage(data));
  }
  return data as T;
}

export async function parseVideo(url: string) {
  const normalizedUrl = normalizeUserUrl(url);
  return request<API.ParseResponse>('/api/parse', {
    method: 'POST',
    body: JSON.stringify({ url: normalizedUrl }),
  });
}

export async function createTask(payload: API.CreateTaskPayload) {
  return request<API.Task>('/api/tasks', {
    method: 'POST',
    body: JSON.stringify({ ...payload, url: normalizeUserUrl(payload.url) }),
  });
}

export async function listTasks(params: { state?: API.Task['state']; limit?: number } = {}) {
  const query = new URLSearchParams();
  if (params.state) query.set('state', params.state);
  if (params.limit) query.set('limit', String(params.limit));
  const suffix = query.toString() ? `?${query.toString()}` : '';
  return request<API.Task[]>(`/api/tasks${suffix}`);
}

export async function cancelTask(taskId: string) {
  return request<API.Task>(`/api/tasks/${taskId}/cancel`, {
    method: 'POST',
  });
}

export async function retryTask(taskId: string) {
  return request<API.Task>(`/api/tasks/${taskId}/retry`, {
    method: 'POST',
  });
}

export async function listTaskEvents(taskId: string) {
  return request<API.TaskEvent[]>(`/api/tasks/${taskId}/events`);
}

export async function getDownloadLink(taskId: string) {
  return request<API.DownloadLink>(`/api/tasks/${taskId}/download-link`);
}

export async function openTaskDownload(taskId: string) {
  const link = await getDownloadLink(taskId);
  window.location.assign(link.url);
}
