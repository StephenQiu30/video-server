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
  preparing: '准备输入',
  analyzing: '执行 AI 分析',
  validating: '校验结构化结果',
  publishing: '发布分析报告',
};

export function screenplayAnalysisErrorMessage(
  code: string | null | undefined,
): string | undefined {
  if (code === 'analysis_resource_limit') {
    return '剧本文本、分块或改写结果超出资源限制，请缩短内容后重试。';
  }
  if (code === 'screenplay_output_incomplete') {
    return '剧本改写结果不完整，任务未发布任何部分正文，请重试。';
  }
  if (
    code === 'analysis_artifact_unavailable' ||
    code === 'input_artifact_unavailable'
  ) {
    return '规范化剧本文档已失效，请重新导入后再分析。';
  }
  if (code === 'invalid_model_output') {
    return 'AI 返回的剧本结果未通过结构、证据或覆盖校验，未发布部分结果。';
  }
  return undefined;
}
