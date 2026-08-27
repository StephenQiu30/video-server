import { describe, expect, it, vi } from 'vitest';

import { request } from '@/lib/request';
import {
  isPrivateThumbnailPath,
  loadPrivateThumbnail,
} from '@/services/media-assets';

vi.mock('@/lib/request', () => ({ request: vi.fn() }));

const THUMBNAIL =
  '/api/inspections/8cba925d-9196-4f48-89ee-76566a705446/thumbnail';
const DOWNLOAD_THUMBNAIL =
  '/api/downloads/8cba925d-9196-4f48-89ee-76566a705446/thumbnail';

describe('media assets', () => {
  it('recognizes private inspection and download thumbnail API paths', () => {
    expect(isPrivateThumbnailPath(THUMBNAIL)).toBe(true);
    expect(isPrivateThumbnailPath(DOWNLOAD_THUMBNAIL)).toBe(true);
    expect(isPrivateThumbnailPath('https://example.com/cover.jpg')).toBe(false);
    expect(isPrivateThumbnailPath('/api/admin/users')).toBe(false);
  });

  it('uses the shared refresh-aware request layer for a valid image', async () => {
    const image = new Blob(['cover'], { type: 'image/jpeg' });
    vi.mocked(request).mockResolvedValue(image);

    await expect(loadPrivateThumbnail(THUMBNAIL)).resolves.toBe(image);
    expect(request).toHaveBeenCalledWith(
      THUMBNAIL,
      expect.objectContaining({ responseType: 'blob' }),
    );
  });

  it('rejects arbitrary paths and invalid responses', async () => {
    await expect(loadPrivateThumbnail('/api/admin/users')).rejects.toThrow(
      'Only private media thumbnail paths are allowed.',
    );

    vi.mocked(request).mockResolvedValue(
      new Blob(['not an image'], { type: 'text/html' }),
    );
    await expect(loadPrivateThumbnail(THUMBNAIL)).rejects.toThrow(
      'Unsupported thumbnail response.',
    );
  });
});
