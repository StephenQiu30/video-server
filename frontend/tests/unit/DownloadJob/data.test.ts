import { describe, expect, it } from 'vitest';
import {
  formatBytes,
  isExpired,
  parseDownloadUrl,
  parseMediaSummary,
} from '@/utils/videoData';

describe('download display data', () => {
  it('keeps unknown estimated sizes readable and validates signed URL protocols', () => {
    expect(formatBytes(null)).toBe('大小未知');
    expect(parseDownloadUrl({ url: 'javascript:alert(1)' })).toBeNull();
    expect(
      parseDownloadUrl({
        url: 'https://minio.example.test/object',
        expires_at: null,
      }),
    ).toEqual({
      url: 'https://minio.example.test/object',
      expiresAt: null,
    });
  });

  it('rejects incomplete media responses and recognizes expiry', () => {
    expect(
      parseMediaSummary({
        id: 'source',
        expires_at: new Date().toISOString(),
        formats: [],
      }),
    ).toBeNull();
    expect(isExpired(new Date(Date.now() - 1).toISOString())).toBe(true);
  });
});
