export const API_BASE_URL = process.env.UMI_APP_API_BASE_URL || 'http://127.0.0.1:8000';

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
    throw new Error(data?.error?.message || data?.message || data?.detail || '请求失败');
  }
  return data as T;
}

export async function parseVideo(url: string) {
  return request<API.ParseResponse>('/api/parse', {
    method: 'POST',
    body: JSON.stringify({ url }),
  });
}

export async function createTask(payload: API.CreateTaskPayload) {
  return request<API.Task>('/api/tasks', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function listTasks() {
  return request<API.Task[]>('/api/tasks');
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
  window.open(link.url, '_blank', 'noopener,noreferrer');
}
