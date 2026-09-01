type Handler = ((event: Event) => void) | null;

export class MockWebSocket {
  static readonly CONNECTING = 0;
  static readonly OPEN = 1;
  static readonly CLOSING = 2;
  static readonly CLOSED = 3;
  static instances: MockWebSocket[] = [];
  static autoOpen = true;

  readonly url: string;
  readyState = MockWebSocket.CONNECTING;
  onopen: Handler = null;
  onclose: Handler = null;
  onerror: Handler = null;
  onmessage: ((event: MessageEvent<string>) => void) | null = null;
  sent: string[] = [];

  constructor(url: string | URL) {
    this.url = String(url);
    MockWebSocket.instances.push(this);
    queueMicrotask(() => {
      if (!MockWebSocket.autoOpen) return;
      this.readyState = MockWebSocket.OPEN;
      this.onopen?.(new Event('open'));
    });
  }

  send(data: string) {
    this.sent.push(data);
  }

  close() {
    this.readyState = MockWebSocket.CLOSED;
    this.onclose?.(new Event('close'));
  }
}

export function emitTaskUpdate(
  taskType: 'analysis' | 'download',
  taskId: string,
  version: number,
) {
  const socket = MockWebSocket.instances.at(-1);
  socket?.onmessage?.(
    new MessageEvent('message', {
      data: JSON.stringify({
        type: 'task.updated',
        event_id: crypto.randomUUID(),
        task_type: taskType,
        task_id: taskId,
        version,
      }),
    }),
  );
}

export function emitTaskSnapshot(
  taskType: 'analysis' | 'download',
  taskId: string,
  version: number,
) {
  const socket = MockWebSocket.instances.at(-1);
  socket?.onmessage?.(
    new MessageEvent('message', {
      data: JSON.stringify({
        type: 'task.snapshot',
        event_id: crypto.randomUUID(),
        task_type: taskType,
        task_id: taskId,
        version,
      }),
    }),
  );
}

export function degradeLatestSocket() {
  const socket = MockWebSocket.instances.at(-1);
  socket?.onerror?.(new Event('error'));
}
