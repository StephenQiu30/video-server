import type { AnalysisJob, AnalysisResult } from '@/types/video';

export const analysisResult: AnalysisResult = {
  language: 'zh-CN',
  title: '如何构建可靠的视频处理流水线',
  summary: {
    text: '视频介绍了从下载、转写到结构化分析的完整处理流程。',
    evidence_segment_ids: ['segment-1'],
  },
  key_points: [
    {
      text: '下载任务和分析任务需要独立建模。',
      evidence_segment_ids: ['segment-1'],
    },
    {
      text: '长任务必须支持状态查询和取消。',
      evidence_segment_ids: ['segment-2'],
    },
  ],
  action_items: [
    {
      text: '为每个异步阶段补充可观测性。',
      evidence_segment_ids: ['segment-2'],
    },
  ],
  chapters: [
    {
      title: '任务建模',
      start_ms: 0,
      end_ms: 62_000,
      summary: '说明下载与分析的任务边界。',
      evidence_segment_ids: ['segment-1'],
    },
  ],
  mind_map: {
    id: 'root',
    title: '视频处理流水线',
    summary: '可靠地处理长耗时视频任务。',
    start_ms: 0,
    evidence_segment_ids: ['segment-1'],
    children: [
      {
        id: 'download',
        title: '视频下载',
        summary: '选择格式并安全下载。',
        start_ms: 5_000,
        evidence_segment_ids: ['segment-1'],
        children: [],
      },
      {
        id: 'analysis',
        title: 'AI 分析',
        summary: '转写后生成结构化结果。',
        start_ms: 32_000,
        evidence_segment_ids: ['segment-2'],
        children: [],
      },
    ],
  },
};

export function analysisJob(
  status: AnalysisJob['status'] = 'queued',
): AnalysisJob {
  return {
    id: '44444444-4444-4444-8444-444444444444',
    profile: 'standard-v1',
    output_language: 'zh-CN',
    status,
    stage: status === 'running' ? 'analyzing' : null,
    progress: status === 'succeeded' ? 100 : status === 'running' ? 60 : 0,
    attempt: status === 'queued' ? 0 : 1,
    error_code: status === 'failed' ? 'provider_unavailable' : null,
    created_at: '2026-08-06T10:01:00Z',
    updated_at: '2026-08-06T10:02:00Z',
    finished_at:
      status === 'succeeded' || status === 'failed' || status === 'cancelled'
        ? '2026-08-06T10:02:00Z'
        : null,
    result: status === 'succeeded' ? analysisResult : null,
  };
}
