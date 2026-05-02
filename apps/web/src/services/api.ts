const API_BASE_URL = process.env.UMI_APP_API_BASE_URL || 'http://127.0.0.1:8000';
const TOKEN_KEY = 'stephen_video_token';

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function logout() {
  localStorage.removeItem(TOKEN_KEY);
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set('Content-Type', 'application/json');
  const token = getToken();
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }
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

export async function register(payload: API.AuthPayload) {
  return request<API.AuthResponse>('/api/auth/register', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function login(payload: Pick<API.AuthPayload, 'email' | 'password'>) {
  return request<API.AuthResponse>('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function getCurrentUser() {
  return request<API.User>('/api/auth/me');
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

export async function getDownloadLink(taskId: string) {
  return request<API.DownloadLink>(`/api/tasks/${taskId}/download-link`);
}
