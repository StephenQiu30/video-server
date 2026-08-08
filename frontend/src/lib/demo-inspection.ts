import type { Inspection, MediaFormat } from '@/types/video';

export const demoInspection: Inspection = {
  id: '00000000-0000-4000-8000-000000000001',
  extractor_key: 'Bilibili',
  provider_media_id: 'BV1x84y1d7QK',
  title: '一支短片，带你看见城市的另一面',
  duration_seconds: 402,
  thumbnail_url: null,
  expires_at: '2026-08-08T18:00:00+08:00',
  formats: [
    demoFormat('4K', 3840, 2160, 'h264', 'mp4'),
    demoFormat('1080P', 1920, 1080, 'h264', 'mp4'),
    demoFormat('720P', 1280, 720, 'vp9', 'webm'),
  ],
};

function demoFormat(
  label: string,
  width: number,
  height: number,
  codec: 'h264' | 'vp9',
  container: 'mp4' | 'webm',
): MediaFormat {
  return {
    id: `00000000-0000-4000-8000-00000000${height}`,
    display_name: `${label} · ${container.toUpperCase()}`,
    plan: {
      width,
      height,
      fps_bucket: 'fps_60',
      dynamic_range: 'sdr',
      video_codec_family: codec,
      audio_codec_family: 'aac',
      audio_language: null,
      container_preference: container,
      compatibility_profile: 'quality',
    },
  };
}
