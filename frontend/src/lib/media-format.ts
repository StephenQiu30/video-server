import type { AudioCodec } from '@/types/video';

export function audioCodecLabel(codec: AudioCodec): string {
  return codec === 'none' ? '无音轨' : codec.toUpperCase();
}
