import type { AnalysisStage, AnalysisStatus } from '@/types/video';

export const statusLabels: Record<AnalysisStatus, string> = {
  queued: '等待分析',
  running: '正在分析',
  retry_wait: '等待重试',
  succeeded: '分析已完成',
  failed: '分析失败',
  cancelled: '分析已取消',
};

export const stageLabels: Record<AnalysisStage, string> = {
  preparing: '准备视频',
  analyzing: '观察画面',
  validating: '校验分镜证据',
  publishing: '发布分析报告',
};
