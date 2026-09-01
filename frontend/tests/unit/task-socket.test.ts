import { afterEach, describe, expect, it, vi } from 'vitest';

import { resolveTaskSocketUrl, taskSocket } from '@/lib/task-socket';
import {
  emitTaskSnapshot,
  emitTaskUpdate,
  MockWebSocket,
} from '../helpers/websocket';

describe('taskSocket snapshots', () => {
  afterEach(() => taskSocket.reset());

  it('accepts a recovery snapshot across a large version gap', async () => {
    const listener = vi.fn();
    const taskId = '44444444-4444-4444-8444-444444444444';
    taskSocket.subscribe('analysis', taskId, 1, listener);
    await Promise.resolve();

    emitTaskSnapshot('analysis', taskId, 130);
    emitTaskUpdate('analysis', taskId, 131);

    expect(listener).toHaveBeenCalledTimes(2);
    expect(listener.mock.calls[0]?.[0]).toMatchObject({
      type: 'task.snapshot',
      version: 130,
    });
    const sent = MockWebSocket.instances.at(-1)?.sent ?? [];
    expect(sent.filter((message) => message.includes('"resync"'))).toHaveLength(
      0,
    );
  });

  it('connects directly to the API port in local development', () => {
    expect(
      resolveTaskSocketUrl({
        environment: 'development',
        location: {
          origin: 'http://localhost:8101',
        },
      }),
    ).toBe('ws://localhost:8111/api/ws/tasks');
  });

  it('uses the secure same-origin task path in production', () => {
    expect(
      resolveTaskSocketUrl({
        environment: 'production',
        location: {
          origin: 'https://frontend.example.com',
        },
      }),
    ).toBe('wss://frontend.example.com/api/ws/tasks');
  });

  it('leaves connecting state and schedules recovery after a stalled handshake', async () => {
    vi.useFakeTimers();
    MockWebSocket.autoOpen = false;
    const statusListener = vi.fn();
    const unsubscribe = taskSocket.subscribe(
      'download',
      '55555555-5555-4555-8555-555555555555',
      0,
      vi.fn(),
      statusListener,
    );
    try {
      expect(statusListener).toHaveBeenLastCalledWith('connecting');
      await vi.advanceTimersByTimeAsync(8_001);
      expect(statusListener).toHaveBeenLastCalledWith('degraded');
      expect(MockWebSocket.instances[0]?.readyState).toBe(MockWebSocket.CLOSED);
    } finally {
      unsubscribe();
      MockWebSocket.autoOpen = true;
      vi.useRealTimers();
    }
  });
});
