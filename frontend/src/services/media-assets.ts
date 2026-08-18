import { request } from '@/lib/request';

const PRIVATE_THUMBNAIL_PATH =
  /^\/api\/inspections\/[0-9a-f-]{36}\/thumbnail$/i;
const SUPPORTED_IMAGE_TYPES = new Set([
  'image/avif',
  'image/jpeg',
  'image/png',
  'image/webp',
]);

export function isPrivateThumbnailPath(
  value: string | null | undefined,
): value is string {
  return Boolean(value && PRIVATE_THUMBNAIL_PATH.test(value));
}

export async function loadPrivateThumbnail(
  path: string,
  signal?: AbortSignal,
): Promise<Blob> {
  if (!isPrivateThumbnailPath(path)) {
    throw new TypeError('Only private inspection thumbnail paths are allowed.');
  }

  const image = await request<Blob>(path, {
    headers: {
      Accept: 'image/avif,image/webp,image/png,image/jpeg',
    },
    responseType: 'blob',
    signal,
  });
  if (image.size === 0 || !SUPPORTED_IMAGE_TYPES.has(image.type)) {
    throw new TypeError('Unsupported thumbnail response.');
  }
  return image;
}
