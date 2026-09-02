import { afterEach, describe, expect, it, vi } from 'vitest';

import { createUuid } from '@/utils/uuid';

describe('createUuid', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('generates an RFC 9562 version 4 UUID without randomUUID', () => {
    const getRandomValues = vi.fn((target: Uint8Array) => {
      target.set(Array.from({ length: 16 }, (_, index) => index));
      return target;
    });
    vi.stubGlobal('crypto', { getRandomValues });

    expect(createUuid()).toBe('00010203-0405-4607-8809-0a0b0c0d0e0f');
    expect(getRandomValues).toHaveBeenCalledOnce();
  });
});
