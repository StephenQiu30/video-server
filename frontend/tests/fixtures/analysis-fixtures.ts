import type { AnalysisJob, AnalysisResult, AnalysisSkill } from '@/types/video';

export const analysisSkills: AnalysisSkill[] = [
  {
    id: 'director-breakdown',
    display_name: '导演拉片',
    description: '按真实 Cut 拆解镜头语言、叙事作用与高光价值。',
    default_prompt: '逐镜头分析画面、叙事作用和高光价值。',
  },
  {
    id: 'highlights',
    display_name: '高光提炼',
    description: '识别传播力和情绪价值较高的片段。',
    default_prompt: '识别高传播力和高情绪价值的片段。',
  },
];

export const analysisResult: AnalysisResult = {
  language: 'zh-CN',
  title: '可靠的视频处理流水线',
  summary: {
    text: '画面展示了下载任务与 AI 分析流程的两个连续分镜。',
    evidence_shot_ids: ['shot-1', 'shot-2'],
  },
  media: { duration_ms: 62_000, container: 'mp4', size_bytes: 1_024_000 },
  shot_count: 2,
  shots: [
    {
      id: 'shot-1',
      index: 1,
      start_ms: 0,
      end_ms: 30_000,
      representative_frame_ms: 15_000,
      description: '宽景展示视频下载任务界面。',
      transition_in: 'none',
      shot_size: 'wide',
      camera_motion: 'static',
      narrative_function: '建立视频处理任务的工作空间。',
      highlight_score: 3,
      visual_tags: ['界面', '下载'],
      asset_ids: ['asset-1'],
    },
    {
      id: 'shot-2',
      index: 2,
      start_ms: 30_000,
      end_ms: 62_000,
      representative_frame_ms: 46_000,
      description: '镜头切换到结构化分析结果。',
      transition_in: 'cut',
      shot_size: 'medium',
      camera_motion: 'static',
      narrative_function: '完成从下载到结构化分析的流程转折。',
      highlight_score: 5,
      visual_tags: ['界面', '分析'],
      asset_ids: [],
    },
  ],
  highlights: [
    {
      id: 'highlight-1',
      title: '流程切换',
      description: '画面从下载任务切换到分析结果。',
      score: 88,
      reason: '这是视觉叙事的主要转折点。',
      start_ms: 30_000,
      end_ms: 62_000,
      evidence_shot_ids: ['shot-2'],
    },
  ],
  assets: [
    {
      id: 'asset-1',
      type: 'logo',
      label: '帧取标志',
      description: '界面左上角的产品标志。',
      first_seen_ms: 0,
      evidence_shot_ids: ['shot-1'],
    },
  ],
  production_advice: {
    summary: '优先还原下载与分析结果之间的流程切换。',
    priority_shot_ids: ['shot-2'],
    recommended_extensions: ['镜头 Prompt', '产品界面资产'],
  },
};

export function analysisJob(
  status: AnalysisJob['status'] = 'queued',
): AnalysisJob {
  return {
    id: '44444444-4444-4444-8444-444444444444',
    run_id: '55555555-5555-4555-8555-555555555555',
    run_no: 1,
    run_trigger: 'initial',
    version: status === 'queued' ? 0 : status === 'running' ? 1 : 2,
    skill_id: 'director-breakdown',
    output_language: 'zh-CN',
    status,
    stage: status === 'running' ? 'analyzing' : null,
    progress: status === 'succeeded' ? 100 : status === 'running' ? 60 : 0,
    attempt: status === 'queued' ? 0 : 1,
    error_code: status === 'failed' ? 'analysis_cli_failed' : null,
    created_at: '2026-08-06T10:01:00Z',
    updated_at: '2026-08-06T10:02:00Z',
    finished_at:
      status === 'succeeded' || status === 'failed' || status === 'cancelled'
        ? '2026-08-06T10:02:00Z'
        : null,
    result: status === 'succeeded' ? analysisResult : null,
    report_markdown:
      status === 'succeeded'
        ? '# 可靠的视频处理流水线 · 逐镜头导演拉片分析报告\n\n## 一、基础信息\n\n已完成分析。\n'
        : null,
    current_report_id:
      status === 'succeeded' ? '66666666-6666-4666-8666-666666666666' : null,
    report:
      status === 'succeeded'
        ? {
            id: '66666666-6666-4666-8666-666666666666',
            status: 'available',
            renderer_version: 'analysis-report-v1',
            content_sha256: 'a'.repeat(64),
            published_at: '2026-08-06T10:02:00Z',
            artifacts: [],
          }
        : null,
  };
}
