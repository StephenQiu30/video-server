import { describe, expect, it } from 'vitest';

import { audioCodecLabel } from '@/lib/media-format';

describe('audioCodecLabel', () => {
  it('localizes a silent video plan', () => {
    expect(audioCodecLabel('none')).toBe('无音轨');
  });

  it('keeps named codecs concise', () => {
    expect(audioCodecLabel('aac')).toBe('AAC');
  });
});
