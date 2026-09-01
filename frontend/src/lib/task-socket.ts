export type TaskSocketStatus =
  | 'connecting'
  | 'connected'
  | 'degraded'
  | 'disconnected';

type TaskType = 'analysis' | 'download';
type Listener = (event: Record<string, unknown>) => void;
type StatusListener = (status: TaskSocketStatus) => void;
type Subscription = {
  taskType: TaskType;
  taskId: string;
  version: number;
  listeners: Set<Listener>;
};

const CONNECT_TIMEOUT_MS = 8_000;

export function resolveTaskSocketUrl({
  environment = process.env.NODE_ENV,
  location = window.location,
}: {
  environment?: string;
  location?: Pick<Location, 'origin'>;
} = {}): string {
  const origin =
    environment === 'development'
      ? localApiOrigin(location.origin)
      : new URL(location.origin);
  origin.protocol =
    origin.protocol === 'https:' || origin.protocol === 'wss:' ? 'wss:' : 'ws:';
  origin.pathname = '/api/ws/tasks';
  origin.search = '';
  origin.hash = '';
  return origin.toString();
}

function localApiOrigin(frontendOrigin: string): URL {
  const origin = new URL(frontendOrigin);
  origin.port = '8111';
  return origin;
}

class TaskSocketManager {
  private socket: WebSocket | null = null;
  private subscriptions = new Map<string, Subscription>();
  private statusListeners = new Set<StatusListener>();
  private status: TaskSocketStatus = 'disconnected';
  private reconnectAttempt = 0;
  private reconnectTimer: number | null = null;
  private connectTimer: number | null = null;

  subscribe(
    taskType: TaskType,
    taskId: string,
    version: number,
    listener: Listener,
    statusListener?: StatusListener,
  ) {
    const key = `${taskType}:${taskId}`;
    const current = this.subscriptions.get(key) ?? {
      taskType,
      taskId,
      version,
      listeners: new Set<Listener>(),
    };
    current.version = Math.max(current.version, version);
    current.listeners.add(listener);
    this.subscriptions.set(key, current);
    if (statusListener) {
      this.statusListeners.add(statusListener);
      statusListener(this.status);
    }
    this.connect();
    if (this.socket?.readyState === WebSocket.OPEN) this.sendSubscribe(current);
    return () => {
      current.listeners.delete(listener);
      if (statusListener) this.statusListeners.delete(statusListener);
      if (current.listeners.size === 0) this.subscriptions.delete(key);
      if (this.subscriptions.size === 0) this.disconnect();
    };
  }

  reset() {
    this.disconnect();
    this.subscriptions.clear();
    this.statusListeners.clear();
    this.reconnectAttempt = 0;
  }

  private connect() {
    if (typeof window === 'undefined' || this.socket) return;
    this.setStatus('connecting');
    let socket: WebSocket;
    try {
      socket = new WebSocket(resolveTaskSocketUrl());
    } catch {
      this.scheduleReconnect();
      return;
    }
    this.socket = socket;
    this.connectTimer = window.setTimeout(() => {
      if (
        this.socket === socket &&
        socket.readyState === WebSocket.CONNECTING
      ) {
        this.setStatus('degraded');
        socket.close();
      }
    }, CONNECT_TIMEOUT_MS);
    socket.onopen = () => {
      if (this.socket !== socket) return;
      this.clearConnectTimer();
      this.reconnectAttempt = 0;
      this.setStatus('connected');
      for (const subscription of this.subscriptions.values()) {
        this.sendSubscribe(subscription);
      }
    };
    socket.onmessage = (message) => this.receive(message.data);
    socket.onerror = () => {
      if (this.socket === socket) this.setStatus('degraded');
    };
    socket.onclose = () => {
      if (this.socket !== socket) return;
      this.clearConnectTimer();
      this.socket = null;
      if (this.subscriptions.size > 0) this.scheduleReconnect();
      else this.setStatus('disconnected');
    };
  }

  private receive(raw: string) {
    let event: Record<string, unknown>;
    try {
      event = JSON.parse(raw) as Record<string, unknown>;
    } catch {
      return;
    }
    if (event.type === 'resync.required') {
      for (const subscription of this.subscriptions.values()) {
        this.sendSubscribe(subscription, 'resync');
      }
      return;
    }
    if (event.type !== 'task.updated' && event.type !== 'task.snapshot') return;
    const taskType = String(event.task_type) as TaskType;
    const taskId = String(event.task_id);
    const version = Number(event.version);
    const subscription = this.subscriptions.get(`${taskType}:${taskId}`);
    if (!subscription || !Number.isSafeInteger(version)) return;
    if (version <= subscription.version) return;
    if (event.type === 'task.snapshot') {
      subscription.version = version;
      for (const listener of subscription.listeners) listener(event);
      return;
    }
    if (version > subscription.version + 1) {
      this.sendSubscribe(subscription, 'resync');
      return;
    }
    subscription.version = version;
    for (const listener of subscription.listeners) listener(event);
  }

  private sendSubscribe(subscription: Subscription, type = 'subscribe') {
    this.socket?.send(
      JSON.stringify({
        type,
        tasks: [
          {
            task_type: subscription.taskType,
            task_id: subscription.taskId,
            after_version: subscription.version,
          },
        ],
      }),
    );
  }

  private scheduleReconnect() {
    this.setStatus('degraded');
    const base = Math.min(30_000, 1_000 * 2 ** this.reconnectAttempt++);
    const delay = base + Math.floor(Math.random() * Math.min(1_000, base / 4));
    this.reconnectTimer = window.setTimeout(() => {
      this.reconnectTimer = null;
      this.connect();
    }, delay);
  }

  private disconnect() {
    if (this.reconnectTimer !== null) window.clearTimeout(this.reconnectTimer);
    this.reconnectTimer = null;
    this.clearConnectTimer();
    const socket = this.socket;
    this.socket = null;
    socket?.close(1000, 'no subscriptions');
    this.setStatus('disconnected');
  }

  private clearConnectTimer() {
    if (this.connectTimer !== null) window.clearTimeout(this.connectTimer);
    this.connectTimer = null;
  }

  private setStatus(status: TaskSocketStatus) {
    this.status = status;
    for (const listener of this.statusListeners) listener(status);
  }
}

export const taskSocket = new TaskSocketManager();
