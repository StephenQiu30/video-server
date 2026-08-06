import { describe, expect, it } from 'vitest';

import { validateMediaUrl } from '@/features/download/validation';

describe('validateMediaUrl', () => {
  it('accepts public-looking HTTP(S) URLs', () => {
    expect(validateMediaUrl('https://media.example/video')).toBeNull();
    expect(validateMediaUrl('http://media.example/video')).toBeNull();
  });

  it('rejects invalid schemes, credentials, and malformed values', () => {
    expect(validateMediaUrl('file:///tmp/video')).toBeTruthy();
    expect(
      validateMediaUrl('https://user:pass@example.com/video'),
    ).toBeTruthy();
    expect(validateMediaUrl('not-a-url')).toBeTruthy();
    expect(validateMediaUrl('')).toBeTruthy();
  });
});
