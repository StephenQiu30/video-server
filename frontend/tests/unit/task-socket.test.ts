import { afterEach, describe, expect, it, vi } from 'vitest';

import { taskSocket } from '@/lib/task-socket';
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
});
