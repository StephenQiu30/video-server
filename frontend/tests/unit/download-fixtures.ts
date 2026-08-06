import type { DownloadJob, Inspection } from '@/types/video';

export const inspection: Inspection = {
  id: '11111111-1111-4111-8111-111111111111',
  extractor_key: 'Controlled',
  provider_media_id: 'video-1',
  title: 'Owned video',
  duration_seconds: 30,
  expires_at: '2026-08-06T11:00:00Z',
  formats: [
    {
      id: '22222222-2222-4222-8222-222222222222',
      display_name: '1080p MP4',
      plan: {
        height: 1080,
        width: 1920,
        fps_bucket: 'fps_30',
        dynamic_range: 'sdr',
        video_codec_family: 'h264',
        audio_codec_family: 'aac',
        audio_language: 'zh-cn',
        container_preference: 'mp4',
        compatibility_profile: 'balanced',
      },
    },
  ],
};

export function job(status: DownloadJob['status'] = 'queued'): DownloadJob {
  return {
    id: '33333333-3333-4333-8333-333333333333',
    inspection_id: inspection.id,
    format_id: inspection.formats[0].id,
    status,
    stage: status === 'running' ? 'downloading' : null,
    progress: status === 'succeeded' ? 100 : status === 'running' ? 35 : 0,
    attempt: status === 'queued' ? 0 : 1,
    error_code: status === 'failed' ? 'download_timeout' : null,
    created_at: '2026-08-06T10:00:00Z',
    updated_at: '2026-08-06T10:00:10Z',
    finished_at: status === 'succeeded' ? '2026-08-06T10:00:10Z' : null,
  };
}
