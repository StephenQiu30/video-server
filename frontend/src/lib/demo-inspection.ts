import type { Inspection, MediaFormat } from '@/types/video';

export const demoInspection: Inspection = {
  id: '00000000-0000-4000-8000-000000000001',
  extractor_key: 'Public media',
  provider_media_id: 'alpine-lake-demo',
  title: '群山与湖泊的早晨',
  duration_seconds: 337,
  media_kind: 'video',
  asset_count: 0,
  thumbnail_url: '/images/media-preview-mountain.webp',
  expires_at: '2026-08-09T11:30:00+08:00',
  source_origin: 'public_url',
  execution_mode: 'provider_runner',
  access_decision: 'downloadable',
  entitlement_state: 'public_free',
  identity_state: 'verified',
  protection_state: 'clear',
  rights_basis: 'public_access',
  restriction_reason: null,
  user_action: null,
  formats: [
    demoFormat('1080P · MP4 · H.264', 1920, 1080, 'h264'),
    demoFormat('720P · MP4 · H.264', 1280, 720, 'h264'),
    demoFormat('480P · MP4 · H.264', 852, 480, 'h264'),
    demoFormat('360P · MP4 · H.264', 640, 360, 'h264'),
  ],
};

function demoFormat(
  displayName: string,
  width: number,
  height: number,
  codec: 'h264' | 'hevc',
): MediaFormat {
  return {
    id: `${codec}-${height}`,
    display_name: displayName,
    plan: {
      width,
      height,
      fps_bucket: 'fps_30',
      dynamic_range: 'sdr',
      video_codec_family: codec,
      audio_codec_family: 'aac',
      audio_language: null,
      container_preference: 'mp4',
      compatibility_profile: codec === 'h264' ? 'balanced' : 'quality',
    },
  };
}
