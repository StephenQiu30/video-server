import { afterEach, expect, it, vi } from 'vitest';
import {
  advanceSessionGeneration,
  withWebSessionMutation,
} from '@/lib/session-events';

afterEach(() => vi.useRealTimers());

it('waits for the origin-wide Cookie writer lock before issuing a mutation', async () => {
  let grant!: () => Promise<unknown>;
  let finish!: (value: unknown) => void;
  const request = vi.fn(
    (_name, _options, callback) =>
      new Promise((resolve) => {
        grant = callback;
        finish = resolve;
      }),
  );
  Object.defineProperty(navigator, 'locks', {
    configurable: true,
    value: { request },
  });
  const mutate = vi.fn(async () => 'signed-in');
  const pending = withWebSessionMutation(mutate);
  expect(mutate).not.toHaveBeenCalled();
  expect(request).toHaveBeenCalledWith(
    'framefetch-web-session-write',
    expect.objectContaining({ signal: expect.any(AbortSignal) }),
    expect.any(Function),
  );
  finish(await grant());
  await expect(pending).resolves.toBe('signed-in');
  expect(mutate).toHaveBeenCalledOnce();
});

it('does not execute a queued Cookie write after identity changes', async () => {
  let grant!: () => Promise<unknown>;
  let reject!: (reason: unknown) => void;
  Object.defineProperty(navigator, 'locks', {
    configurable: true,
    value: {
      request: (
        _name: string,
        _options: LockOptions,
        callback: () => Promise<unknown>,
      ) =>
        new Promise((_resolve, fail) => {
          grant = callback;
          reject = fail;
        }),
    },
  });
  const mutate = vi.fn(async () => undefined);
  const pending = withWebSessionMutation(mutate);
  const rejected = expect(pending).rejects.toMatchObject({
    code: 'session_changed',
  });
  advanceSessionGeneration();
  try {
    await grant();
  } catch (error) {
    reject(error);
  }
  await rejected;
  expect(mutate).not.toHaveBeenCalled();
});

it('bounds lock waiting and does not fall back to an uncoordinated write', async () => {
  vi.useFakeTimers();
  Object.defineProperty(navigator, 'locks', {
    configurable: true,
    value: {
      request: (_name: string, options: LockOptions) =>
        new Promise((_resolve, reject) =>
          options.signal?.addEventListener('abort', () =>
            reject(new DOMException('Aborted', 'AbortError')),
          ),
        ),
    },
  });
  const mutate = vi.fn(async () => undefined);
  const pending = withWebSessionMutation(mutate);
  const rejected = expect(pending).rejects.toMatchObject({
    code: 'session_busy',
  });
  await vi.advanceTimersByTimeAsync(30_000);
  await rejected;
  expect(mutate).not.toHaveBeenCalled();
});

it('rejects unsupported browser contexts before sending credentials', async () => {
  Object.defineProperty(navigator, 'locks', {
    configurable: true,
    value: undefined,
  });
  const mutate = vi.fn(async () => undefined);
  await expect(withWebSessionMutation(mutate)).rejects.toMatchObject({
    code: 'browser_session_unavailable',
  });
  expect(mutate).not.toHaveBeenCalled();
});
