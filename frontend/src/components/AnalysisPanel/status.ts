import type { AnalysisStage, AnalysisStatus } from '@/types/video';

export const statusLabels: Record<AnalysisStatus, string> = {
  queued: '等待分析',
  running: '分析中',
  retry_wait: '等待重试',
  succeeded: '分析已完成',
  failed: '分析失败',
  cancelled: '分析已取消',
};

export const stageLabels: Record<AnalysisStage, string> = {
  preparing: '准备视频',
  transcribing: '转写音频',
  analyzing: '理解内容',
  validating: '校验结果',
};

export const cancellableAnalysisStatuses = new Set<AnalysisStatus>([
  'queued',
  'running',
  'retry_wait',
]);