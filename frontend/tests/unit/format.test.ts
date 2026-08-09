import { describe, expect, it } from 'vitest';

import { formatDuration, formatMilliseconds } from '@/utils/format';

describe('formatDuration', () => {
  it('formats mm:ss when under an hour', () => {
    expect(formatDuration(30)).toBe('0:30');
    expect(formatDuration(65)).toBe('1:05');
    expect(formatDuration(3599)).toBe('59:59');
  });

  it('formats h:mm:ss at or above an hour', () => {
    expect(formatDuration(3600)).toBe('1:00:00');
    expect(formatDuration(3725)).toBe('1:02:05');
    expect(formatDuration(7325)).toBe('2:02:05');
  });

  it('formats milliseconds', () => {
    expect(formatMilliseconds(30_000)).toBe('0:30');
    expect(formatMilliseconds(3_625_000)).toBe('1:00:25');
  });
});
