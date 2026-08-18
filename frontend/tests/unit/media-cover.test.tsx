import { render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import MediaCover from '@/components/media-cover';
import { loadPrivateThumbnail } from '@/services/media-assets';

vi.mock('@/services/media-assets', async (importOriginal) => {
  const actual =
    await importOriginal<typeof import('@/services/media-assets')>();
  return {
    ...actual,
    loadPrivateThumbnail: vi.fn(),
  };
});

const THUMBNAIL =
  '/api/inspections/8cba925d-9196-4f48-89ee-76566a705446/thumbnail';

describe('MediaCover', () => {
  afterEach(() => {
    vi.clearAllMocks();
    vi.mocked(URL.createObjectURL).mockReset();
  });

  it('loads a private thumbnail through the authenticated refresh-aware client', async () => {
    const image = new Blob(['cover'], { type: 'image/jpeg' });
    vi.mocked(loadPrivateThumbnail).mockResolvedValue(image);
    vi.mocked(URL.createObjectURL).mockReturnValue('blob:private-thumbnail');
    const revoke = vi.spyOn(URL, 'revokeObjectURL');

    const view = render(<MediaCover alt="测试视频" src={THUMBNAIL} />);

    expect(
      screen.getByRole('img', { name: '测试视频（封面加载中）' }),
    ).toBeVisible();
    await waitFor(() =>
      expect(screen.getByRole('img', { name: '测试视频' })).toHaveAttribute(
        'src',
        'blob:private-thumbnail',
      ),
    );
    expect(loadPrivateThumbnail).toHaveBeenCalledWith(
      THUMBNAIL,
      expect.any(AbortSignal),
    );

    view.unmount();
    expect(revoke).toHaveBeenCalledWith('blob:private-thumbnail');
  });

  it('shows unavailable only after the authenticated thumbnail request fails', async () => {
    vi.mocked(loadPrivateThumbnail).mockRejectedValue(
      new Error('storage unavailable'),
    );

    render(<MediaCover alt="测试视频" src={THUMBNAIL} />);

    await waitFor(() =>
      expect(
        screen.getByRole('img', { name: '测试视频（封面不可用）' }),
      ).toBeVisible(),
    );
  });

  it('keeps public and bundled images on the direct browser path', () => {
    render(<MediaCover alt="演示视频" src="/images/demo.webp" />);

    expect(screen.getByRole('img', { name: '演示视频' })).toHaveAttribute(
      'src',
      'http://localhost:3000/images/demo.webp',
    );
    expect(loadPrivateThumbnail).not.toHaveBeenCalled();
  });
});
